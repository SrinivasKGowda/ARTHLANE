# Free server on Oracle Cloud

Oracle's Always Free tier includes an Arm server that is enough for Arthlane. These steps replace steps 1, 4 and 5 of [README.md](README.md); do the rest of that guide as written.

## 1. Create the account

1. Open <https://www.oracle.com/in/cloud/free/> and choose **Start for free**.
2. Choose an **Individual** account and use your real name and address. They must match your card.
3. **Home region:** pick **India West (Mumbai)** or **India South (Hyderabad)**. You cannot change it later, and free servers only run in your home region.
4. **Card:** use a Visa or Mastercard with online and international payments switched on. Oracle uses it only to verify you (it may place a small temporary charge) and does not bill you unless you upgrade.
5. Set up the two-step sign-in Oracle asks for.

Stay on the free account; do not click **Upgrade**.

## 2. Create the server

Menu → **Compute** → **Instances** → **Create instance**:

| Setting | Choose |
| --- | --- |
| Name | `arthlane` |
| Image | **Change image** → Ubuntu → **Canonical Ubuntu 24.04** |
| Shape | **Change shape** → Ampere → **VM.Standard.A1.Flex**, **2 OCPUs, 4 GB memory** (shows "Always Free-eligible") |
| Networking | Create a new virtual cloud network and a new **public** subnet; **assign a public IPv4 address** |
| SSH keys | **Generate a key pair for me** → **Download private key**. Save it as `C:\Users\srini\.ssh\arthlane.key`. Without this file you cannot log in. |
| Boot volume | Leave the default |

Choose **Create** and note the **Public IP address** on the instance page.

If you see "Out of capacity for shape VM.Standard.A1.Flex", choose another availability domain under **Placement**, or try again later; free capacity frees up through the day.

**Why 4 GB and not the full 12 GB:** Oracle reclaims free servers that look idle for 7 days, meaning processor, network *and* memory use all stay under 20%. Arthlane uses about 1–1.3 GB of memory, which keeps a 4 GB server above that line; on a 12 GB server it would look idle.

## 3. Open the web ports in Oracle's network

Menu → **Networking** → **Virtual cloud networks** → your network → **Security Lists** → **Default Security List** → **Add Ingress Rules**. Add two rules:

| Source CIDR | IP protocol | Destination port range |
| --- | --- | --- |
| `0.0.0.0/0` | TCP | `80,443` |
| `0.0.0.0/0` | UDP | `443` |

SSH (port 22) is already open.

## 4. Log in from your PC

In PowerShell (the first line stops Windows from refusing a key file that others could read):

```powershell
icacls "$env:USERPROFILE\.ssh\arthlane.key" /inheritance:r /grant:r "${env:USERNAME}:R"
ssh -i "$env:USERPROFILE\.ssh\arthlane.key" ubuntu@YOUR_SERVER_IP
```

Type `yes` when asked about the fingerprint.

## 5. Prepare the server

Oracle's Ubuntu has its own firewall that blocks everything except SSH, so do not turn on `ufw`. Open the web ports in it **before** installing Docker:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p udp --dport 443 -j ACCEPT
sudo netfilter-persistent save

sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
```

Do not run `netfilter-persistent save` again after Docker is installed; it would save Docker's own rules and break networking after a reboot.

## 6. Copy the code

From PowerShell on your PC, in `D:\SrinisStore (1)`:

```powershell
tar -czf arthlane.tgz --exclude=target --exclude=data --exclude=__pycache__ --exclude=.env market-oracle arthlane-backend deploy
scp -i "$env:USERPROFILE\.ssh\arthlane.key" arthlane.tgz ubuntu@YOUR_SERVER_IP:/tmp/
```

On the server:

```bash
sudo mkdir -p /opt/arthlane && sudo tar -xzf /tmp/arthlane.tgz -C /opt/arthlane
sudo -i
```

`sudo -i` makes you the administrator for the remaining commands. Now continue with **step 6 of README.md**. Use this step again whenever README.md says to copy the files.

After the site is running, check memory with `free -m`: **used** should be more than a fifth of **total**.
