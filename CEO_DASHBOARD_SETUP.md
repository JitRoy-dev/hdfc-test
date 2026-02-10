# CEO Dashboard - Teams and Employees Feature

## Overview
The CEO Dashboard feature allows CEOs to view all teams (Keycloak groups) and their employee members through a REST API endpoint.

## Features
- **View All Teams**: Fetch all groups configured in Keycloak
- **View Team Members**: For each team, see all employee members
- **Employee Information**: Display employee details (username, email, name, status)
- **Summary Statistics**: Total teams and total employees count
- **Token Caching**: Admin tokens are cached for 5 minutes to optimize performance

## API Endpoint
```
GET /ceo
Authorization: Bearer <access-token>
```

### Response Example
```json
{
  "ceo": {
    "username": "ceo.user",
    "email": "ceo@example.com",
    "name": "CEO Name"
  },
  "teams": [
    {
      "id": "group-uuid-1",
      "name": "Sales Team",
      "path": "/Sales Team",
      "subGroupCount": 0,
      "members": [
        {
          "id": "user-uuid-1",
          "username": "john.smith",
          "email": "john@example.com",
          "firstName": "John",
          "lastName": "Smith",
          "enabled": true
        },
        {
          "id": "user-uuid-2",
          "username": "jane.doe",
          "email": "jane@example.com",
          "firstName": "Jane",
          "lastName": "Doe",
          "enabled": true
        }
      ]
    },
    {
      "id": "group-uuid-2",
      "name": "Engineering Team",
      "path": "/Engineering Team",
      "subGroupCount": 0,
      "members": [...]
    }
  ],
  "totalTeams": 2,
  "totalEmployees": 5
}
```

## Setup Instructions

### 1. Create Admin Client in Keycloak
The CEO dashboard uses Keycloak's Admin API to fetch groups and their members. You need to create a dedicated admin client:

**Steps:**
1. Open Keycloak Admin Console
2. Navigate to your realm
3. Go to **Clients** section
4. Click **Create client** button
5. Enter Client ID (e.g., `fastapi-admin`)
6. Select **OpenID Connect** as Client Protocol
7. Click **Create**

### 2. Configure Service Account
1. In the client settings, find **Service accounts** section
2. Toggle **Service accounts enabled** to ON
3. Click **Save**
4. Go to the **Service Accounts Roles** tab
5. Click **Assign role** and add the following realm roles:
   - `manage-users`
   - `view-groups`
   - `query-groups`
   - `view-realm`

### 3. Get Client Credentials
1. Go to the **Credentials** tab
2. Copy the **Client Secret**

### 4. Configure Environment Variables
Update your `.env` file or Docker/Kubernetes environment with:
```
KEYCLOAK_ADMIN_CLIENT_ID=fastapi-admin
KEYCLOAK_ADMIN_CLIENT_SECRET=<copied-client-secret>
```

## Key Components

### `keycloak_admin.py`
New module that provides:
- `get_admin_token()`: Authenticates with Keycloak using service account credentials
- `get_groups()`: Fetches all groups from Keycloak
- `get_group_members()`: Fetches members of a specific group
- `get_groups_with_members()`: Convenience function combining all above

### `routes.py` Updates
- Updated `/ceo` endpoint to fetch and return teams with employees
- Proper error handling with HTTP 500 status on failures
- Endpoint requires `ceo` role for access

## Security Considerations

1. **Admin Credentials**: Keep `KEYCLOAK_ADMIN_CLIENT_SECRET` secure in environment variables only, never commit to git
2. **Role-Based Access**: Only users with `ceo` role can access the `/ceo` endpoint
3. **Token Caching**: Admin tokens are cached for 5 minutes to reduce exposure
4. **Error Handling**: Failures are logged but don't expose sensitive server details to clients

## Troubleshooting

### "No admin credentials configured"
- Ensure `KEYCLOAK_ADMIN_CLIENT_ID` and `KEYCLOAK_ADMIN_CLIENT_SECRET` are set in environment variables
- Check that the admin client exists in Keycloak

### "401 Unauthorized" fetching groups
- Verify the admin client secret is correct
- Check that the service account has the required roles assigned
- Ensure the admin client has "Service accounts enabled"

### "Failed to fetch groups"
- Verify Keycloak server is running and accessible
- Check network connectivity between the backend and Keycloak server
- Review logs for detailed error messages

### Empty groups or members
- Verify that groups exist in your Keycloak realm
- Ensure users are properly assigned to groups in Keycloak

## Example Frontend Usage

### Using Fetch API
```javascript
async function getCEODashboard() {
  const response = await fetch('/ceo', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch CEO dashboard: ${response.statusText}`);
  }
  
  const data = await response.json();
  
  // Display teams and employees
  console.log(`Found ${data.totalTeams} teams with ${data.totalEmployees} employees`);
  
  data.teams.forEach(team => {
    console.log(`Team: ${team.name}`);
    team.members.forEach(member => {
      console.log(`  - ${member.firstName} ${member.lastName} (${member.email})`);
    });
  });
}
```

## Performance Notes

- **Token Caching**: Admin tokens are cached for 5 minutes to reduce authentication overhead
- **Concurrent Requests**: Multiple group member requests are made in parallel
- **Error Resilience**: If one group's members fail to fetch, others continue loading
- **Recommend**: Cache the entire response on the frontend for 5-10 minutes for better UX

## Future Enhancements

Potential improvements for future versions:
- Filter teams by department or cost center
- Search employees by name or email
- Export team data to CSV
- Hierarchical group support (sub-groups)
- Pagination for large datasets
- Real-time member count synchronization
