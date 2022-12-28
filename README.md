![](https://nyc3.digitaloceanspaces.com/startram/anchor.png)

# NativePlanet Self-Hosted anchor

This is a self-hostable version of the NativePlanet anchor service. The installer script is meant to be run on Debian/Ubuntu, but it should work on other distros if you have Python 3 & Ansible installed. 

### How to use

You'll need set a few things up ahead of time:

- Spin up a VPS (e.g. [DigitalOcean](https://m.do.co/c/94f7fdc03fad) or [Vultr](https://www.vultr.com/?ref=9235764)) and make note of the IP address
  - This package is designed to run on Ubuntu 22.04; it works well with typical ~$5 1GB/1CPU instances though could work reasonably on a 512MB/1CPU instance.
  - The playbook will automatically provision 2GB swap -- this doesn't work on some hosts, so if it breaks it, just comment out those lines and try again.
- Register a domain (you can re-use an existing one, you'll only be using subdomains)

Create the following 5 `A` records for your domain, assigned to your VPS's IP address:
  - `anchor.yourdomain.com` -- the anchor URL your NP will connect to
  - `ship-name.yourdomain.com` -- The URL of your ship's name
  - `s3.ship-name.yourdomain.com` -- These 3 subdomains for Minio
  - `console.s3.ship-name.yourdomain.com`
  - `bucket.s3.ship-name.yourdomain.com`

If you want to run multiple ships, create new subdomains for them (you only need one `anchor` record).

Make sure you can connect to the VPS over SSH as root with an SSH key.
- If you don't have a key, you can generate one with `ssh-keygen -t ed25519 -m PEM -f id_ed25519`
- Copy the contents of your public key from `id_ed25519.pub`
- Get the public key for your keyfile with `ssh-keygen -f ./id_ed25519 -y` if you don't see one
- Connect to your VPS, and use `sudo su -` to switch to `root`
- Open `/root/.ssh/authorized_keys` in a text editor and paste in the public key for your key
- Run `systemctl restart sshd`

Clone this git repository on your local computer:

```
git clone https://github.com/Native-Planet/anchor.git
cd anchor
```

Open the `settings.sh` file in a text editor and edit the variables, with the root of your domain (`yourdomain.com`), `REG_CODE` as the code you'll use to register your device (🚨 **change this!** 🚨), and the path to the pem file you just generated.

Run `./install.sh` to execute the installer script; it will connect to your VPS (using the `anchor.yourdomain.com` IP address) and download and configure all of the software automatically. Wait until the ansible playbook has completed -- this might take a few minutes on low-spec servers.

On your NativePlanet, go to the settings menu and under the Anchor submenu, select 'custom endpoint' and enter `anchor.yourdomain.com`.