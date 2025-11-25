# Admin Features - User Management

## What's New

I've integrated the admin user management functionality from the previous conversation. Here's what's available:

## Admin Access

**Requirements:**
- Must have ADMIN or SUPERUSER role
- Admin user created by `init_db.py` has SUPERUSER role

**Admin Navigation:**
- Admins see an "Admin" link in the navigation bar
- Takes you to the admin dashboard

## Admin Features

### 1. Admin Dashboard (`/admin/`)
**Statistics Display:**
- Total users count
- Active users count  
- Total projects count
- Total beams count
- Recent users list

**Quick Actions:**
- Manage Users
- Create New User
- Manage Products (placeholder for SUPERUSER)
- Manage Standards (placeholder for SUPERUSER)

### 2. User Management (`/admin/users`)
**User List with:**
- Username, email, role
- Active/inactive status with color indicators
- Project count per user
- Last login and created dates
- Actions: Edit, Activate/Deactivate, Delete

**Role Color Coding:**
- SUPERUSER: Red (#dc3545)
- ADMIN: Orange (#F69321)
- DETAILER: Blue (#0066B3)
- USER: Gray (#6c757d)

### 3. Create User (`/admin/users/create`)
**Fields:**
- Username (required, unique)
- Email (required, unique)
- Password (required, min 6 chars)
- Role selection:
  - USER - View only
  - DETAILER - Create/edit projects and beams (default)
  - ADMIN - User management
  - SUPERUSER - Full system access (only visible to SUPERUSER)

### 4. Edit User (`/admin/users/<id>/edit`)
**Can Update:**
- Email
- Password (optional - leave blank to keep current)
- Role
- Active status (checkbox)

**Shows:**
- User information (created date, last login, project count)
- Username is read-only (cannot be changed)

### 5. User Actions

**Toggle Active/Inactive:**
- Quick toggle from user list
- Cannot deactivate your own account
- Deactivated users cannot log in

**Delete User (SUPERUSER only):**
- Permanently delete user
- Cascades: Deletes all user's projects and beams
- Cannot delete your own account
- Requires confirmation

## Permissions

### ADMIN can:
- View admin dashboard
- View all users
- Create new users
- Edit users (email, role, password, status)
- Activate/deactivate users

### SUPERUSER can (in addition to ADMIN):
- Delete users
- Create other SUPERUSER accounts
- Access to product/standards management (when implemented)

## URLs

```
/admin/                          - Admin dashboard
/admin/users                     - User list
/admin/users/create             - Create new user
/admin/users/<id>/edit          - Edit user
/admin/users/<id>/toggle-active - Toggle active status (POST)
/admin/users/<id>/delete        - Delete user (POST, SUPERUSER only)
```

## Access Control

**All admin routes check:**
1. User is authenticated
2. User has ADMIN or SUPERUSER role
3. Cannot modify own account status or delete self
4. SUPERUSER-only actions are protected

**Non-admin users who try to access:**
- Get "Access denied" flash message
- Redirected to projects list

## Testing

**Login as admin:**
- Username: `admin`
- Password: `admin123`
- Role: SUPERUSER (full access)

**Test scenarios:**
1. Create a new DETAILER user
2. Edit their role to ADMIN
3. Log in as that user - should see Admin link
4. Create another user
5. Toggle active status
6. Try to delete (won't work - need SUPERUSER)
7. Log back in as admin
8. Delete the test user

## Security Features

- Password hashing with bcrypt
- Role-based access decorators
- Cannot self-destruct (deactivate/delete own account)
- Cascade deletes warn about data loss
- SUPERUSER-only delete action
- Active status prevents login without deleting data

## Future Enhancements

Placeholders in dashboard for:
- Product management
- Standards management  
- System settings
- Usage analytics

## Files Updated/Created

**New Files:**
- `app/routes/admin.py` - Admin routes and logic
- `app/templates/admin/dashboard.html` - Admin dashboard
- `app/templates/admin/users.html` - User list
- `app/templates/admin/user_form.html` - Create/edit form

**Updated Files:**
- `app/__init__.py` - Register admin blueprint
- `app/templates/base.html` - Add Admin nav link

## Notes

- User counts in dashboard use lazy queries for efficiency
- Project count per user uses relationship count
- All forms have validation and flash messages
- Consistent Lumberbank branding throughout
- Responsive table layout
