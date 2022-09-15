# NativePlanet Self-Hosted Relay

This is a self-hostable version of the NativePlanet anchor service. The installer script is meant to be run on Debian/Ubuntu, but it should work on other distros if you comment out the line with the `apt` commands and have Python 3 & Ansible installed. 

### How to use

You'll need set a few things up ahead of time:

- Spin up a VPS (e.g. [DigitalOcean](https://m.do.co/c/94f7fdc03fad) or [Vultr](https://vultr.com))and make note of the IP address
  - This package is designed to run on Ubuntu 22.04; it works well with typical ~$5 1GB/1CPU instances though could work reasonably on a 512MB/1CPU instance.
- Register a domain (you can re-use an existing one, you'll only be using subdomains)

Create the following 5 `A` records for your domain, assigned to your VPS's IP address:
  - `relay.yourdomain.com`
  - `ship-name.yourdomain.com`
  - `s3.ship-name.yourdomain.com`
  - `console.s3.ship-name.yourdomain.com`
  - `bucket.s3.ship-name.yourdomain.com`
  - Optional: `db.your-domain.com` (for debugging)

If you want to run multiple ships or MinIO instances, create new subdomains for them (you only need one `relay` record).

Make sure you can connect to the VPS over SSH as root with a `.pem` SSH public key.
- If you don't have a `.pem` file, you can generate one with `ssh-keygen -t ed25519 -m PEM`
- Get the public key for your `.pem` file with `ssh-keygen -f /path/to/key.pem -y`
- Connect to your VPS, and use `sudo su -` to switch to `root`
- Open `/root/.ssh/authorized_keys` in a text editor and paste in the public key for your key
- Run `systemctl restart sshd`

Clone this git repository:

```
git clone https://github.com/Native-Planet/relay.git
cd relay
```

Open the `settings.sh` file in a text editor and edit the variables, with the root of your domain (`yourdomain.com`), `REG_CODE` as the code you'll use to register your device (**be sure to change this!**), and the path to the pem file you just generated. You can optionally enable a DB visualizer for debugging, but you can safely ignore it (do not leave it running during normal use).

Run `./install.sh` to execute the installer script; it will connect to your VPS (using the `relay.yourdomain.com` IP address) and download and configure all of the software automatically. Wait until the ansible playbook has completed -- this might take a few minutes on low-spec servers.

On your NativePlanet, go to the settings menu and under the Anchor submenu, select 'custom endpoint' and enter `relay.yourdomain.com`.