---
description: Create a single dummy user in the database
allowed-tools: Read, Bash(python3:*)
---

Read database/db.py to understand the users table 
schema and the get_db() helper.

Then run a Python script INLINE using Bash (do NOT create 
any .py file — use heredoc syntax exactly like this):

Bash: python3 << 'EOF'
# script 
EOF

The script should:

1. Generate a realistic random Indian user using your 
   own knowledge of common Indian names across regions:
   - Name: a realistic Indian first + last name
   - Email: derived from the name with a random 2-3 digit 
     number suffix (e.g. rahul.sharma91@gmail.com)
   - Password: "password123" hashed with werkzeug's 
     generate_password_hash
   - created_at: current datetime

2. Check if the generated email already exists in the 
   users table. If it does, regenerate until unique.

3. Insert the user into the database using the same 
   get_db() pattern found in db.py.

4. Print confirmation:
   - id
   - name
   - email