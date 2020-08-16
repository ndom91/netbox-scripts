# Newtelco Netbox Scripts

Custom scripts currently running in our [Netbox](https://github.com/netbox-community/netbox) instance.

#### 1. Create VM on Proxmox

Place `create_vm.py` into the `/netbox/netbox/scripts` subfolder. 

When opening in Netbox, you will have the ability to define the following fields:

- VM Name
- CPU Cores
- RAM
- Disk Size
- DNS Hostname
- Cluster
- Notes

After making sure 'Commit' is checked and submitting the form, Netbox will add the VM documentation and this script will talk to your Proxmox cluster via the [proxmoxer](https://pypi.org/project/proxmoxer/) Python library to create the VM as defined by you as well as the disk on `local-zfs` of your chosen Proxmox host. 

- [Proxmox API Docs](https://pve.proxmox.com/pve-docs/api-viewer/index.html)
- [Netbox Template](https://github.com/netbox-community/reports/blob/master/scripts/create_vm.py)

### License

MIT
