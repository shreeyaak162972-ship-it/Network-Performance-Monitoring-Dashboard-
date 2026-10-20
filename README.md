# Network Performance Monitoring Dashboard

A web-based network performance monitoring dashboard built with Flask and PostgreSQL. The project uses Docker Compose to run the web application and database, along with the configured demo device agents.

> **Demo-data note:** The configured PC agents generate simulated/demo metrics. This setup does not automatically monitor real physical computers unless real agents are installed and configured separately.

## Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Run with Docker](#run-with-docker-recommended)
- [Application URLs](#application-urls)
- [PostgreSQL Terminal Guide](#postgresql-terminal-guide)
- [Debugging and Logs](#debugging-and-logs)
- [Stop and Restart](#stop-and-restart)
- [Run Python Dependencies Locally](#run-python-dependencies-locally-optional)
- [GitHub Setup](#github-setup)
- [Team Setup and Database Sharing](#team-setup-and-database-sharing)
- [Security Notes](#security-notes)

## Features

- User registration and login
- Dashboard for viewing device/network metrics
- PostgreSQL database
- Docker-based local development
- Configured demo device agents

## Technology Stack

- Python
- Flask
- PostgreSQL
- Docker and Docker Compose
- HTML, CSS, and JavaScript

## Requirements

Install the following on your computer:

- Docker Desktop (start it before running the commands)
- Git (only required to clone or push the repository)
- A modern web browser

You do not need to install PostgreSQL separately when using the Docker setup.

## Run with Docker (Recommended)

Run the following commands in **PowerShell / Windows Terminal**.

### 1. Download the repository

Replace the placeholders with the actual GitHub username and repository name:

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

If you already have the project downloaded, open PowerShell in the project folder that contains `docker-compose.yml` instead.

### 2. Configure environment variables

If the repository contains `.env.example`, create your local `.env` file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set the required local values, including the database password, then save and close Notepad. Keep `.env` private and never commit it to GitHub.

If `.env.example` is not present, check the environment variables used by `docker-compose.yml` and the application configuration before creating `.env`. Do not guess secret values.

### 3. Build and start the containers

From the project root:

```powershell
docker compose up -d --build
```

Check container status:

```powershell
docker compose ps
```

View recent logs:

```powershell
docker compose logs --tail 100
```

### 4. Open the application

- Register: <http://127.0.0.1:5000/register>
- Login: <http://127.0.0.1:5000/login>
- Dashboard: <http://127.0.0.1:5000/dashboard>

Register a user, then log in to open the dashboard.

## Application URLs

| Purpose | URL |
|---|---|
| Registration | `http://127.0.0.1:5000/register` |
| Login | `http://127.0.0.1:5000/login` |
| Dashboard | `http://127.0.0.1:5000/dashboard` |

The application must be running in Docker for these URLs to work. Do not use VS Code Live Server for the Flask application.

## PostgreSQL Terminal Guide

The Docker Compose database service is named `db`. The database name used by this project is `network_monitoring`.

### 1. Open PostgreSQL

Run this command in PowerShell from the project folder:

```powershell
docker compose exec db psql -U postgres -d network_monitoring
```

You should now see a PostgreSQL prompt similar to:

```text
network_monitoring=#
```

The commands in the next section are run **inside PostgreSQL**, not in PowerShell.

### 2. List databases and tables

```text
\l
\dt
```

- `\l` lists databases.
- `\dt` lists tables in the current database.

### 3. Inspect table structures

```text
\d users
\d device_metrics
```

These commands show the columns and types for the named tables. If a table is not found, run `\dt` to check the table names in your version of the project.

### 4. Query database records

Count users:

```sql
SELECT COUNT(*) FROM users;
```

Count device metric records:

```sql
SELECT COUNT(*) FROM device_metrics;
```

Show recent device metric records:

```sql
SELECT * FROM device_metrics ORDER BY id DESC LIMIT 20;
```

These queries assume the listed tables exist. If a query reports that a table or column does not exist, inspect the schema using `\dt` and `\d table_name` and adjust the query to match the actual schema. SQL statements must end with a semicolon (`;`).

### 5. Run one query directly from PowerShell

You do not need to open the interactive PostgreSQL prompt for a quick check:

```powershell
docker compose exec db psql -U postgres -d network_monitoring -c "SELECT COUNT(*) FROM device_metrics;"
```

### 6. Exit PostgreSQL

Inside the PostgreSQL prompt, run:

```text
\q
```

This returns you to PowerShell.

### 7. Check database status and logs

```powershell
docker compose ps db
docker compose logs --tail 100 db
```

Follow database logs live (press `Ctrl+C` to stop following logs):

```powershell
docker compose logs -f db
```

### Optional: connect with pgAdmin or DBeaver

For a GUI connection from the same computer, use the following values **if they match the port mapping and environment in your Compose configuration**:

- Host: `127.0.0.1`
- Port: `5433`
- Database: `network_monitoring`
- Username: `postgres`
- Password: the local `POSTGRES_PASSWORD` value configured in `.env`

If the connection fails, verify the port mapping in `docker-compose.yml` and the local credentials. Do not expose PostgreSQL directly to the public internet.

## Debugging and Logs

Run these commands from the project root.

### Check all containers

```powershell
docker compose ps
```

### View web application logs

```powershell
docker compose logs --tail 100 web
```

### View database logs

```powershell
docker compose logs --tail 100 db
```

### Follow web logs live

```powershell
docker compose logs -f web
```

Press `Ctrl+C` to stop following logs. This stops viewing the logs; it does not stop the containers.

### Rebuild the web application after code changes

```powershell
docker compose up -d --build web
```

If you changed the Docker configuration or dependencies, rebuild all services:

```powershell
docker compose up -d --build
```

### Common problems

**Docker command is not recognized**
- Install Docker Desktop, reopen PowerShell, and confirm Docker Desktop is running.

**The page does not open**
- Run `docker compose ps`.
- Check `docker compose logs --tail 100 web`.
- Confirm the web service maps host port `5000`.

**A port is already in use**
- Another application may already use port `5000` or `5433`.
- Check the port mappings in `docker-compose.yml` and resolve the conflict before restarting.

**The database connection fails**
- Check `docker compose ps db` and `docker compose logs --tail 100 db`.
- Verify the database name and credentials in the local configuration.
- From another container, the database hostname is usually the Compose service name `db`; `127.0.0.1` inside a container refers to that same container, not the database container.

**A PostgreSQL table or column is not found**
- Enter PostgreSQL and run `\dt`, then inspect the relevant table with `\d table_name`.
- Use the actual table and column names shown by PostgreSQL.

**The dashboard looks unchanged after a frontend update**
- Rebuild the web service if needed, then hard-refresh the browser with `Ctrl+F5`.

## Stop and Restart

Stop the containers but keep the database volume and its data:

```powershell
docker compose down
```

Start the existing setup again:

```powershell
docker compose up -d
```

**Warning:** This command can delete the database volume and its data:

```powershell
docker compose down -v
```

Only run it if you intentionally want to erase the local database data.

## Run Python Dependencies Locally (Optional)

The Docker workflow is the recommended way to run this project. If you need to install Python packages directly on Windows, run these commands from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs packages only. It does not start PostgreSQL or replace the Docker Compose setup. The app may also require environment variables and supporting services from Docker Compose.

## GitHub Setup

### First push to a new GitHub repository

Create an empty repository on GitHub. Then run the following commands from the project folder. Replace the placeholders with your real values:

```powershell
git init
git status
git add .
git status
git commit -m "Initial project setup"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

If Git is already initialized, do not repeat `git init` unnecessarily. If a remote is already configured, check it with:

```powershell
git remote -v
```

Do not run `git remote add origin ...` if `origin` already exists.

### Push later updates

Review the files before staging them:

```powershell
git status
git add README.md requirements.txt
git commit -m "Update project documentation"
git push
```

Add other files explicitly if you changed them and want to include them in the commit.

## Team Setup and Database Sharing

Every teammate should:

1. Install and start Docker Desktop.
2. Clone the repository.
3. Create their own private `.env` file from `.env.example`, if provided.
4. Run `docker compose up -d --build`.
5. Open `http://127.0.0.1:5000/register` and create a local account.

Each laptop has its own PostgreSQL database by default. Pushing code to GitHub does not share database records from one laptop with another.

To share records, use an approved shared database or a sanitized sample-data/backup process. Never publish private user data, credentials, `.env` files, or sensitive database backups.

## Security Notes

- Never commit `.env` files, passwords, secret keys, or database credentials.
- Check `git status` before every commit.
- If a secret was committed, removing it from the latest commit alone may not remove it from Git history; rotate the exposed secret.
- Do not expose PostgreSQL directly to the public internet.
- Use simulated metrics only as demo data unless real monitoring agents have been configured.

