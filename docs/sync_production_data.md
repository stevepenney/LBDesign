# Syncing Production Data to Localhost

How to pull a copy of the live DigitalOcean database down to your local dev environment for
testing. The DB is a **managed** DigitalOcean database — it only accepts connections from
Trusted Sources, so you can't just point `dumpdata` at it from your laptop. Instead, run the dump
*inside* the app's own environment (which already has DB access) via the DO App Platform web
Console, then get the resulting file off the container via DO Spaces.

## 1. Dump the data (in the DO App Platform Console)

Open the app's **Console** tab in the DigitalOcean dashboard (a shell into the running
container — it already has `DATABASE_URL` set and the app's own dependencies installed) and run:

```bash
python manage.py dumpdata \
  -e contenttypes -e auth.permission -e auth.group -e admin.logentry -e sessions \
  --indent 2 > data.json
```

The `-e` excludes matter — `contenttypes`/`auth.permission`/`auth.group`/`admin.logentry`/
`sessions` are meant to be regenerated locally by each environment's own migrations, not
transferred. Skipping this step doesn't break the dump, but it will make `loaddata` fail locally
later (see **Troubleshooting** below) — that filtering can be done after the fact instead if
you forget.

## 2. Get the file out of the console

The console is a plain terminal — there's no download button, and copy/paste of a multi-MB file
out of a browser terminal is unreliable (screenshots/OCR of long text is *especially* unreliable
for anything security-sensitive like a signed URL — a single mistyped character breaks it). The
app already has `boto3` and `django-storages` installed with the Spaces credentials live as env
vars, so push the file to the `lb-design` Space instead, still from the same console session
(`python manage.py shell`):

```python
import boto3
from django.conf import settings

s3 = boto3.client(
    's3',
    region_name=settings.AWS_S3_REGION_NAME,
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

key = 'tmp/data.json'
s3.upload_file('data.json', settings.AWS_STORAGE_BUCKET_NAME, key, ExtraArgs={'ACL': 'private'})

url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
    ExpiresIn=600,  # 10 minutes
)
print(url)
```

Note this deliberately uses `boto3` directly with `ACL: 'private'` + a short-lived presigned URL,
**not** `default_storage.save()` — the app's default storage config uses `AWS_DEFAULT_ACL =
'public-read'` (fine for static/media assets meant to be public) but a full DB dump shouldn't
sit at a permanent public URL.

Download the printed URL on your laptop (browser, or `curl -o data.json "<url>"`) within the
10-minute window, then delete the temp copy from the same shell:

```python
s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
```

If the console won't let you select/copy the printed URL at all, upload with
`ExtraArgs={'ACL': 'public-read'}` instead and use the plain object URL
(`https://lb-design.syd1.digitaloceanspaces.com/tmp/data.json`) — much shorter and easier to
retype by hand than a signed URL, at the cost of a brief public-exposure window. Delete the
object as soon as you've downloaded it either way.

## 3. Reset your local DB and load the dump

```bash
venv/Scripts/python manage.py flush
venv/Scripts/python manage.py loaddata data.json
```

`loaddata` never deletes anything — it upserts by primary key, so any local-only row (leftover
dummy/test data) that isn't in the dump would otherwise be left behind mixed in with production
data, and Postgres's auto-increment sequences wouldn't be advanced to match the loaded IDs
(risking an `IntegrityError` on the next record you create). `flush` avoids both problems: it
truncates every table and resets the identity sequences in one step, so the load starts from a
clean slate. It'll ask for confirmation before wiping your local data.

### Troubleshooting: `Permission matching query does not exist` / `M2MDeserializationError`

If the dump was taken without the `-e` excludes from step 1, `loaddata` will fail on
`auth.group`/`auth.permission` — production's permission table can carry stale codenames left
over from old model renames that don't match what your local migrations regenerate. `loaddata`
runs the whole file as one transaction, so a failure here leaves your DB cleanly empty (from the
`flush`), not half-loaded. Filter the offending tables out of the file and load that instead:

```bash
venv/Scripts/python -c "
import json

with open('data.json', encoding='utf-8') as f:
    objects = json.load(f)

EXCLUDE_MODELS = {'contenttypes.contenttype', 'auth.permission', 'auth.group', 'admin.logentry', 'sessions.session'}
STRIP_M2M_FIELDS = ('groups', 'user_permissions')

kept = []
for obj in objects:
    if obj['model'] in EXCLUDE_MODELS:
        continue
    for field in STRIP_M2M_FIELDS:
        if field in obj.get('fields', {}) and obj['fields'][field]:
            obj['fields'][field] = []
    kept.append(obj)

with open('data_filtered.json', 'w', encoding='utf-8') as f:
    json.dump(kept, f)
"
venv/Scripts/python manage.py loaddata data_filtered.json
```

## 4. Sanity check

```bash
venv/Scripts/python manage.py check
venv/Scripts/python manage.py showmigrations   # confirm nothing shows [ ] (unapplied)
```

`data.json`/`data_filtered.json` are both gitignored — never commit them, they contain full
production data.
