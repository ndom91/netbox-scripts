"""
This script allows you to create a VM, an interface and primary IP address
all in one screen.

Workaround for issues:
https://github.com/netbox-community/netbox/issues/1492
https://github.com/netbox-community/netbox/issues/648
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

def format_size(avail, unit="MB"):
    """ Converts integers to common size units used in computing """
    bit_shift = {"B": 0,
            "kb": 7,
            "KB": 10,
            "mb": 17,
            "MB": 20,
            "gb": 27,
            "GB": 30,
            "TB": 40,}
    return "{:,.0f}".format(avail / float(1 << bit_shift[unit])) + " " + unit

def pve_getAvail():
    proxmox = ProxmoxAPI(addr, user='root@pam',
        token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)

def pve_getImages(addr):
    proxmox = ProxmoxAPI(addr, user='root@pam',
        token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)

    DISK_IMAGES = ()
    content=node.storage('local-zfs').content['local'].get()
    log_info(content)
    foo = DiskImage.objects.create(pk=1)
    foo.add(content)
    foo.save()
    return foo

class NewVM(Script):
    class Meta:
        name = "New VM"
        description = "Create a new VM"
        field_order = ['vm_name', 'dns_name', 'primary_ip4', 'primary_ip6', #'vrf',
                       'role', 'status', 'cluster', #'tenant',
                       'platform', 'interface_name', 'mac_address',
                       'vcpus', 'memory', 'disk', 'comments', 'pve_host', 'pve_images', 'storage1']

    proxmox = ProxmoxAPI('192.168.11.203', user='root@pam',
        token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)

    vm_name = StringVar(label="Name")
    dns_name = StringVar(label="DNS Name", required=True, default="HOST.newtelco.local")
    # dns_name = StringVar(label="DNS name", required=False)
    primary_ip4 = IPAddressWithMaskVar(label="IPv4 address", required=False, default="192.168.11.")
    # primary_ip6 = IPAddressWithMaskVar(label="IPv6 address", required=False)
    # vrf = ObjectVar(VRF.objects, required=False)
    # role = ObjectVar(DeviceRole.objects.filter(vm_role=True), required=False, default=8)
    # status = ChoiceVar(VirtualMachineStatusChoices, default=VirtualMachineStatusChoices.STATUS_ACTIVE)
    cluster = ObjectVar(Cluster.objects, default="4")
    # tenant = ObjectVar(Tenant.objects, required=False)
    # platform = ObjectVar(Platform.objects, required=False)
    # interface_name = StringVar(default="eth0")
    # mac_address = StringVar(label="MAC address", required=False)
    vcpus = IntegerVar(label="vCPUs", required=True)
    memory = IntegerVar(label="Memory (MB)", required=True)
    disk = IntegerVar(label="Disk (GB)", required=True)
    comments = TextVar(label="Comments", required=False)
    node = proxmox.nodes('nt-pve')
    # self.log_info(choices=node.storage.local.content.get())
    # storage1 = ChoiceVar(choices=node.storage.local.content.get())
    # disk_images = ChoiceVar(choices=node.storage.local.content.get())
    # disk_images = ObjectVar(
			# description="Disk Images",
			# widget=APISelect(
					# api_url='https://192.168.11.203:8006/api2/json/nodes/nt-pve/storage/local/content',
					# queryset=DeviceRole.objects.all(),
    #       additional_query_params={"PVEAuthCookie": "0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d"}
					# # display_field='model',
					# # additional_query_params={'model': ['Catalyst 3560X-48T', 'Catalyst 3750X-48T']}
			# ))
		# }

    # pve_host = ObjectVar(Device.objects.filter(cluster__name='Newtelco Cluster'), label="Proxmox Host", required=True)
    PVE_DEVICES = (
        ('nt-pve', 'nt-pve'),
        ('nt-pve2', 'nt-pve2'),
        ('nt-pve5', 'nt-pve5'),
        ('nt-pve6', 'nt-pve6')
    )
    pve_host = ChoiceVar(choices=PVE_DEVICES)
    # disk_images = ChoiceVar(choices=pve_getImages())
    # pve_host_ip=Device.objects.filter(name=pve_host)

    def run(self, data, commit):
        # self.log_info(data["storage1"])
        pve_host=Device.objects.filter(name=data["pve_host"])
        pve_ip=str(pve_host.get().primary_ip4)[:-3]

        vm = VirtualMachine(
            name=data["vm_name"],
            vcpus=data["vcpus"],
            memory=data["memory"],
            disk=data["disk"],
            comments=data["comments"],
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

        def add_addr(addr, expect_family):
            if not addr:
                return
            if addr.version != expect_family:
                raise RuntimeError("Wrong family for %r" % a)
            try:
                a = IPAddress.objects.get(
                    address=addr,
                    family=addr.version,
                )
                result = "Assigned"
            except ObjectDoesNotExist:
                a = IPAddress(
                   address=addr,
                   family=addr.version,
                )
                result = "Created"
            a.status = IPAddressStatusChoices.STATUS_ACTIVE
            a.dns_name = data["dns_name"]
            if a.interface:
                raise RuntimeError("Address %s is already assigned" % addr)
            a.interface = interface
            # a.tenant = data.get("tenant")
            a.save()
            self.log_info("%s IP address %s %s" % (result, a.address, a.vrf or ""))
            setattr(vm, "primary_ip%d" % a.family, a)

        def connect_pve(addr):
            # self.log_info(addr)
            proxmox = ProxmoxAPI(addr, user='root@pam', password="",
                                         token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)
            # self.log_success(proxmox.nodes.get())
            node = proxmox.nodes(data["pve_host"])
            # self.log_info(node.storage.local.content.get())
            # self.log_success(node)
            # self.log_info(node.storage('local-zfs').status.get())
            # avail=format_size(node.storage('local-zfs').status.get()["avail"], "GB")
            # total=format_size(node.storage('local-zfs').status.get()["total"], "GB")
            # self.log_info(avail)
            # self.log_info(total)

            nextId = proxmox.cluster.nextid.get()
            disk = data["disk"]
            ipAddr = data["primary_ip4"]

            # CREATE VM
            if commit: 
                node.qemu.create(vmid=nextId,
                    cdrom="local:iso/ubuntu-20.04.1-live-server-amd64.iso",
                    name=data["vm_name"],
                    storage="local",
                    memory=data["memory"],
                    cores=data["vcpus"],
                    net0="model=virtio,bridge=vmbr0",
                    ostype="l26",
                    scsi0=f"local-zfs:vm-{nextId}-disk-0:{disk}G",
                    ipconfig0=f"gw=192.168.11.1,ip={ipAddr}",
                    agent="enabled=1")
                self.log_success("Created VM {0} ({1})".format(vm.name, nextId))

        # self.log_info(data["pve_host"])
        # self.log_info(pve_ip)
        connect_pve(pve_ip)
        if commit:
            add_addr(data["primary_ip4"], 4)
            # add_addr(data["primary_ip6"], 6)
            vm.save()
            self.log_success("Created VM %s" % vm.name)
        else:
            self.log_success("Dry-run Success - Created VM %s" % vm.name)
