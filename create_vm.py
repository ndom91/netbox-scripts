"""
This script allows you to create a VM, an interface and primary IP address
all in one screen and call the Proxmox API to actually create said VM.
"""

from django.db import models
from pathlib import Path
from dcim.choices import InterfaceTypeChoices
from dcim.models import Device, DeviceRole, Platform, Interface
from django.core.exceptions import ObjectDoesNotExist
from ipam.choices import IPAddressStatusChoices
from ipam.models import IPAddress, VRF
from tenancy.models import Tenant
from virtualization.choices import VirtualMachineStatusChoices
from virtualization.models import Cluster, VirtualMachine
from extras.scripts import Script, StringVar, IPAddressWithMaskVar, ObjectVar, ChoiceVar, IntegerVar, TextVar
from utilities.forms import APISelect
from proxmoxer import ProxmoxAPI

class NewVM(Script):
    class Meta:
        name = "New VM"
        description = "Create a new VM"
        commit_default = False
        field_order = ['vm_name', 'dns_name', 'cluster', 'vcpus', 'memory', 'disk', 'comments', 'pve_host']

    vm_name = StringVar(label="Name")
    dns_name = StringVar(label="DNS Name", required=True, default=".newtelco.local")
    cluster = ObjectVar(Cluster.objects, default="4")
    vcpus = IntegerVar(label="CPU Cores", required=True, default="2")
    memory = IntegerVar(label="RAM (MB)", required=True, description="i.e. 1024")
    disk = IntegerVar(label="Disk (GB)", required=True, description="i.e. 15")
    notes = TextVar(label="Notes", required=False)

    PVE_DEVICES = (
        ('nt-pve', 'nt-pve'),
        ('nt-pve2', 'nt-pve2'),
        ('nt-pve5', 'nt-pve5'),
        ('nt-pve6', 'nt-pve6')
    )
    # trying to get the ChoiceVar to dynamically list available PVE nodes
    # proxmox = ProxmoxAPI('192.168.11.203', user='root@pam',
        # token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)
    # nodes = proxmox.nodes().get()

    # pve_host = ChoiceVar(choices=nodes, label="Proxmox Host", required=True)
    pve_host = ChoiceVar(choices=PVE_DEVICES, label="Proxmox Host", required=True)

    def run(self, data, commit):

        def add_addr(addr, expect_family):
            if not addr:
                return
            if addr.version != expect_family:
                raise RuntimeError("Wrong family for %r" % a)
            try:
                a = IPAddress.objects.get(
                    address=addr,
                )
                result = "Assigned"
            except ObjectDoesNotExist:
                a = IPAddress(
                   address=addr,
                )
                result = "Created"
            a.status = IPAddressStatusChoices.STATUS_ACTIVE
            a.dns_name = data["dns_name"]
            if a.interface:
                raise RuntimeError("Address %s is already assigned" % addr)
            a.interface = interface
            a.save()
            self.log_info("%s IP address %s %s" % (result, a.address, a.vrf or ""))
            setattr(vm, "primary_ip%d" % a.family, a)

        def create_pve_vm(addr):
            proxmox = ProxmoxAPI(addr, user='root@pam', password="",
                                         token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)
            node = proxmox.nodes(data["pve_host"])
            nextId = proxmox.cluster.nextid.get()
            disk=data["disk"]

            # CREATE VM
            if commit:
                node.qemu.create(
                    vmid=nextId,
                    cdrom="local:iso/ubuntu-20.04.1-live-server-amd64.iso",
                    name=data["vm_name"],
                    storage="local",
                    memory=data["memory"],
                    cores=data["vcpus"],
                    net0="model=virtio,bridge=vmbr0",
                    ostype="l26",
                    scsihw="virtio-scsi-pci",
                    scsi0=f"local-zfs:vm-{nextId}-disk-0,size={disk}G",
                    agent="enabled=1")

                localStorage = node.storage('local-zfs')
                localStorage.content.create(
                    filename=f"vm-{nextId}-disk-0",
                    size=f"{disk}G",
                    vmid=f"{nextId}",
                    format="raw"
                )

                self.log_success("Created VM {0} ({1})".format(vm.name, nextId))

        pve_host=Device.objects.filter(name=data["pve_host"])
        pve_ip=str(pve_host.get().primary_ip4)[:-3]

        vm = VirtualMachine(
            name=data["vm_name"],
            vcpus=data["vcpus"],
            memory=data["memory"],
            disk=data["disk"],
            comments=data["notes"],
            cluster=data["cluster"]
        )
        if commit:
            vm.save()

        interface = Interface(
            name="eth0",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            virtual_machine=vm,
        )
        if commit:
            interface.save()

        if commit:
            create_pve_vm(pve_ip)
            vm.save()
            self.log_success("Created VM %s" % vm.name)
        else:
            self.log_success("Dry-run Success - Created VM %s" % vm.name)
