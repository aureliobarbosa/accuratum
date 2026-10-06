Empty on purpose. `firebase.json` needs a `public` folder, but Firebase
Hosting serves a file from here *before* applying the rewrite to Cloud Run,
so a copy of the site's static files here would shadow what the service
serves. Everything comes from the Cloud Run service. This file is in
`firebase.json`'s `ignore` list, so it's never uploaded.
