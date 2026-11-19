# Children's Bible Study Group web UI

Angular 22 admin interface for the Children's Bible Study Group. It talks to the FastAPI backend through the
`/v1` proxy configured in `proxy.conf.json`.

```bash
npm ci
npm start        # http://localhost:4200
npm run build
npm test -- --watch=false
```

The API must be running on `http://localhost:8000` (see the repository README).
