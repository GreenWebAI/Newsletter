# Newsletter
Check these 6 URLs for new posts published since yesterday. For each new post, give me title, link, and 2-sentence summary. If nothing new, say so.

## How it works

A GitHub Actions workflow (`.github/workflows/newsletter.yml`) runs every morning
at **08:00 UTC**, executes `newsletter.py`, and emails a digest of posts published
in the last 24 hours. Each entry includes its title, link, and a ~2-sentence
summary. If nothing is new, the email says so.

### Setup

1. **Add your feeds.** Edit [`feeds.txt`](feeds.txt) and list one RSS/Atom feed
   URL per line (the README mentions 6 URLs — replace the placeholders). Most
   blogs expose a feed at `/feed`, `/rss`, `/atom.xml`, or `/index.xml`.

2. **Configure email secrets.** In the repo: **Settings → Secrets and variables →
   Actions → New repository secret**. Add:

   | Secret          | Required | Description                                            |
   | --------------- | -------- | ------------------------------------------------------ |
   | `SMTP_HOST`     | yes      | SMTP server hostname (e.g. `smtp.gmail.com`)           |
   | `EMAIL_TO`      | yes      | Recipient(s), comma-separated                          |
   | `SMTP_PORT`     | no       | Default `587`                                          |
   | `SMTP_USERNAME` | no\*     | SMTP login                                             |
   | `SMTP_PASSWORD` | no\*     | SMTP password / app password / API key                 |
   | `SMTP_SECURITY` | no       | `starttls` (default), `ssl`, or `none`                 |
   | `EMAIL_FROM`    | no       | Sender address (defaults to `SMTP_USERNAME`)           |
   | `EMAIL_SUBJECT` | no       | Subject prefix (default `Newsletter digest`)           |

   \*Required by most providers. For Gmail use an [App Password](https://support.google.com/accounts/answer/185833).

3. **Done.** The workflow runs daily on its own. You can also trigger it manually
   from the **Actions** tab (**Run workflow**), where a `dry_run` option prints the
   digest to the job log instead of sending email.

### Run locally

```bash
pip install -r requirements.txt
DRY_RUN=1 python newsletter.py          # print the digest, don't send
```

