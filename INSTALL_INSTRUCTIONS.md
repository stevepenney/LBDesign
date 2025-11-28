# LBDesign Calculation Engine Update Package

## 📦 What's in This Package

```
lbdesign_update/
├── migrate_add_calculation_fields.py    ← Run this FIRST to update database
├── test_calculations.py                 ← Test script (optional)
└── app/
    ├── models/
    │   └── beam.py                      ← Updated Beam model (REPLACES existing)
    └── services/
        └── calculations/                ← NEW directory with calculation engine
            ├── __init__.py
            ├── structural_mechanics.py
            ├── design_factors.py
            └── calculation_service.py
```

## 🚀 Installation Steps

### Step 1: Backup Your Database (IMPORTANT!)

```bash
# Create a backup of your current database
cp instance/beam_selector.db instance/beam_selector.db.backup
```

### Step 2: Extract This Package

Extract the zip file to your project root directory. It will preserve the correct folder structure.

```bash
# If you're in your project root (where run.py is):
unzip lbdesign_calculation_engine_update.zip
```

This will create:
- `migrate_add_calculation_fields.py` in your project root
- `app/services/calculations/` directory with all calculation modules
- Updated `app/models/beam.py`

### Step 3: Run the Database Migration

```bash
python migrate_add_calculation_fields.py
```

**Expected Output:**
```
📊 Current beams table structure:
   - id (INTEGER)
   - project_id (INTEGER)
   - name (VARCHAR(100))
   ... (your existing columns)

📦 Found X existing beam(s) in database
   ⚠️  Migration will preserve all existing data

🔧 Adding new calculation fields...
  ✅ Added column 'demand_moment'
  ✅ Added column 'demand_shear'
  ... (12 columns total)

✅ Database migration completed successfully!
   Added 12 new column(s)
```

### Step 4: Verify Migration

The script automatically verifies:
- All new columns were added
- Existing data was preserved
- Beam count remains the same

If you see any errors, restore your backup:
```bash
cp instance/beam_selector.db.backup instance/beam_selector.db
```

### Step 5: Test the Calculation Engine (Optional)

```bash
python test_calculations.py
```

This runs unit tests on all calculation formulas to verify they work correctly.

### Step 6: Restart Your Application

```bash
python run.py
```

## ✅ What Changed

### Database Changes (12 New Columns Added to `beams` table)

**Demands:**
- `demand_moment` - M* (kNm)
- `demand_shear` - V* (kN)
- `demand_deflection` - δ (mm)

**Capacities:**
- `capacity_moment` - φMn (kNm)
- `capacity_shear` - φVn (kN)
- `deflection_limit` - δ_limit (mm)

**Utilization:**
- `utilization_moment` - M*/φMn
- `utilization_shear` - V*/φVn
- `utilization_deflection` - δ/δ_limit

**Metadata:**
- `calc_status` - "PASS", "WARNING", "FAIL"
- `calc_version` - Version of calculation used
- `calc_date` - When calculated

### File Changes

**REPLACED:**
- `app/models/beam.py` - Now includes calculation result fields and new properties

**NEW:**
- `app/services/calculations/__init__.py`
- `app/services/calculations/structural_mechanics.py` - Physics formulas
- `app/services/calculations/design_factors.py` - NZS3603 factors
- `app/services/calculations/calculation_service.py` - Orchestration

## 🔧 Next Steps (Integration)

After installation, you'll need to add the calculation functionality to your UI:

### 1. Add Calculate Route

In `app/routes/beams.py`, add:

```python
from app.services.calculations import calculate_and_update_beam

@beams_bp.route('/<int:beam_id>/calculate', methods=['POST'])
@login_required
def calculate(beam_id):
    """Calculate beam and update results"""
    from app.extensions import db
    
    beam = BeamRepository.get_by_id(beam_id)
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    # Check permissions
    if beam.project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    # Run calculation
    updated_beam, results = calculate_and_update_beam(beam)
    db.session.commit()
    
    flash(f'Calculation complete: {results["calc_status"]}', 'success')
    return redirect(url_for('beams.detail', beam_id=beam.id))
```

### 2. Add Calculate Button

In `app/templates/beams/detail.html`, add after beam properties:

```html
{% if not beam.is_calculated or request.args.get('recalculate') %}
<form method="POST" action="{{ url_for('beams.calculate', beam_id=beam.id) }}" style="display: inline;">
    <button type="submit" class="btn btn-primary">Calculate</button>
</form>
{% else %}
<form method="POST" action="{{ url_for('beams.calculate', beam_id=beam.id) }}" style="display: inline;">
    <button type="submit" class="btn btn-secondary">Re-calculate</button>
</form>
{% endif %}
```

### 3. Display Results

Add to `app/templates/beams/detail.html`:

```html
{% if beam.is_calculated %}
<div class="card">
    <h2>Calculation Results 
        <span style="background-color: 
            {% if beam.calc_status == 'PASS' %}#22c55e
            {% elif beam.calc_status == 'WARNING' %}#f59e0b
            {% else %}#ef4444{% endif %};
            color: white; padding: 0.25rem 0.75rem; border-radius: 4px;">
            {{ beam.calc_status }}
        </span>
    </h2>
    
    <h3>Demands vs Capacities</h3>
    <table>
        <tr>
            <th></th>
            <th>Demand</th>
            <th>Capacity</th>
            <th>Utilization</th>
        </tr>
        <tr>
            <td><strong>Bending:</strong></td>
            <td>{{ "%.2f"|format(beam.demand_moment) }} kNm</td>
            <td>{{ "%.2f"|format(beam.capacity_moment) }} kNm</td>
            <td>{{ "%.1f"|format(beam.utilization_moment * 100) }}%</td>
        </tr>
        <tr>
            <td><strong>Shear:</strong></td>
            <td>{{ "%.2f"|format(beam.demand_shear) }} kN</td>
            <td>{{ "%.2f"|format(beam.capacity_shear) }} kN</td>
            <td>{{ "%.1f"|format(beam.utilization_shear * 100) }}%</td>
        </tr>
        <tr>
            <td><strong>Deflection:</strong></td>
            <td>{{ "%.2f"|format(beam.demand_deflection) }} mm</td>
            <td>{{ "%.2f"|format(beam.deflection_limit) }} mm</td>
            <td>{{ "%.1f"|format(beam.utilization_deflection * 100) }}%</td>
        </tr>
    </table>
    
    <p><strong>Controlling factor:</strong> {{ beam.controlling_factor }}</p>
    <p><small>Calculated: {{ beam.calc_date.strftime('%Y-%m-%d %H:%M') }} | Version: {{ beam.calc_version }}</small></p>
</div>
{% endif %}
```

## 📚 Documentation

Full documentation available in the separate `calculation_engine` folder:
- `README.md` - Quick reference
- `CALCULATION_ENGINE_IMPLEMENTATION.md` - Complete implementation guide

## 🆘 Troubleshooting

### Migration Script Errors

**Error: "table beams has no column named X"**
- This is expected if column doesn't exist yet - script will add it

**Error: "duplicate column name"**
- Column already exists - script will skip it safely

**Error: "no such table: beams"**
- Run `python init_db.py` first to create tables

### After Migration

**Import Error: "No module named 'app.services.calculations'"**
- Make sure you extracted files to the correct location
- Check that `app/services/calculations/__init__.py` exists

**Calculation Returns Wrong Values**
- Run `python test_calculations.py` to verify formulas
- Check that beam input parameters are in correct units

## 🔄 Rolling Back (If Needed)

If you need to undo the changes:

```bash
# Restore database backup
cp instance/beam_selector.db.backup instance/beam_selector.db

# Remove new files
rm -rf app/services/calculations/

# Restore old beam.py (if you have a backup)
# Otherwise, comment out the new fields in beam.py
```

## 📞 Support

If you encounter any issues:
1. Check that your backup is safe
2. Review the error messages from migration script
3. Run test_calculations.py to verify formulas
4. Check file permissions

## ✅ Verification Checklist

After installation, verify:
- [ ] Database migration completed successfully
- [ ] All 12 columns added to beams table
- [ ] Existing data preserved (beam count unchanged)
- [ ] Test script runs without errors
- [ ] Application starts without import errors
- [ ] Can view existing beams without errors

Once verified, you're ready to add the calculate button and display results!
