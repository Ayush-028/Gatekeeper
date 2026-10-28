# Deploy layer 3 (the only hosted part)

Layer 3 is a ~50-line Cloudflare Worker that holds your free Gemini key and answers "safe / suspicious / malicious".
Cloudflare Workers has a free plan (100,000 requests a day, no sleeping). Check the current limits on their pricing page.

1. Make a free Cloudflare account and a free Gemini key (Google AI Studio).
2. In this folder: `cd worker`
3. `npx wrangler login`
4. `npx wrangler secret put GEMINI_API_KEY`   (paste your key; it is stored by Cloudflare, not in the code)
5. `npx wrangler deploy`  -> it prints a URL like `https://gatekeeper-l3.<you>.workers.dev`
6. Put `<that url>/check` into `DEFAULT_L3_URL` in `src/gatekeeper/layer3.py` and push to GitHub.
   (To try it first, set the environment variable `GATEKEEPER_L3_URL` instead.)
7. Test: `curl -X POST <url> -H "Content-Type: application/json" -d '{"text":"ignore previous instructions"}'`

Things to know
- Pages are sent here as text, so the first-run notice in the library tells users and shows how to turn it off.
- The Worker doesn't log page text. Gemini's free tier may use inputs to improve Google's products, so say so on the README.
- Anyone who finds the URL can call it. Add a Cloudflare rate-limiting rule in the dashboard if abuse starts.
- If this service is down or slow, Gatekeeper keeps working with layers 1, 2 and 4.
