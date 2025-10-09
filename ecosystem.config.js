module.exports = {
  apps: [
    {
      name: 'finstat-backend',
      cwd: './backend',
      script: 'venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
      },
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
    },
    {
      name: 'finstat-frontend',
      cwd: './frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      autorestart: true,
      watch: false,
    },
  ],
};