# Wi-Fi and VPN

> Network names and URLs below are placeholders — swap them for the real ones.

## I can't find the office Wi-Fi network

1. Click the Wi-Fi icon in the top-right of your screen.
2. Look for **Office-5G**. If you only see **Office-Guest**, you're on the
   visitor network — it works, but it's slower and blocks some internal tools.
3. Can't see **Office-5G** at all? Turn Wi-Fi off, wait five seconds, turn it
   back on. It usually reappears.
4. Still nothing after that — post in #it-help. You may not be on the network
   allowlist yet, and we have to add you manually.

## My Wi-Fi keeps dropping

This is almost always one of three things. Work down the list.

1. **You're on the wrong network.** Click the Wi-Fi icon and check you're on
   **Office-5G**, not **Office-Guest**. Guest drops connections by design.
2. **Your Mac is clinging to a weak signal.** Hold the Option key and click the
   Wi-Fi icon — you'll see extra detail. If **RSSI** is worse than -70, you're
   too far from an access point. Move rooms and see if it settles.
3. **The connection is stale.** Click the Wi-Fi icon → Wi-Fi Settings → find
   **Office-5G** → click the three dots → **Forget This Network**. Then join it
   again with the password from 1Password.

If it still drops after all three, tell us in #it-help *which* of these you
tried and where you were sitting. That saves us twenty minutes.

## I need the Wi-Fi password

It's in 1Password, in the **Everyone** vault, under **Office Wi-Fi**.

If you can't get into 1Password, that's the real problem — see the
passwords and logins guide.

## I'm working from home and can't reach an internal tool

Some tools only accept connections from the office network or the VPN.
If a link works in the office and not at home, you need the VPN on.

1. Open **Tailscale** from the menu bar at the top of your screen.
2. If it says *Disconnected*, click **Connect**.
3. Wait for it to say *Connected*, then reload the page.

## The VPN says connected but nothing loads

1. Click **Disconnect**, wait ten seconds, click **Connect** again. This fixes
   it most of the time.
2. If it doesn't: quit Tailscale completely (right-click the menu bar icon →
   Quit), reopen it, and connect again.
3. Still stuck — check whether a normal website like google.com loads. If that
   fails too, the problem is your home internet, not the VPN.

## I'm being asked to log into the VPN again and again

Your session has expired, which is normal and happens every 30 days.
Sign in with your Google work account. If the login window won't appear at
all, restart your Mac — it's a known glitch and a restart clears it.
