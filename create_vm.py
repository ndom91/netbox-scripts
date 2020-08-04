"""
This script allows you to create a VM, an interface and primary IP address
all in one screen.

Workaround for issues:
https://github.com/netbox-community/netbox/issues/1492
https://github.com/netbox-community/netbox/issues/648
"""

from dcim.choices import InterfaceTypeChoices
from dcim.models import Device, DeviceRole, Platform, Interface
from django.core.exceptions import ObjectDoesNotExist
from ipam.choices import IPAddressStatusChoices
from ipam.models import IPAddress, VRF
from tenancy.models import Tenant
from virtualization.choices import VirtualMachineStatusChoices
from virtualization.models import Cluster, VirtualMachine
from extras.scripts import Script, StringVar, IPAddressWithMaskVar, ObjectVar, ChoiceVar, IntegerVar, TextVar
from proxmoxer import ProxmoxAPI

class NewVM(Script):
    class Meta:
        name = "New VM"
        description = "Create a new VM"
        field_order = ['vm_name', 'dns_name', 'primary_ip4', 'primary_ip6', #'vrf',
                       'role', 'status', 'cluster', #'tenant',
                       'platform', 'interface_name', 'mac_address',
                       'vcpus', 'memory', 'disk', 'comments', 'pve_host']

    vm_name = StringVar(label="VM name")
    dns_name = StringVar(label="DNS name", required=False)
    primary_ip4 = IPAddressWithMaskVar(label="IPv4 address")
    # primary_ip6 = IPAddressWithMaskVar(label="IPv6 address", required=False)
    # vrf = ObjectVar(VRF.objects, required=False)
    role = ObjectVar(DeviceRole.objects.filter(vm_role=True), required=False, default=8)
    status = ChoiceVar(VirtualMachineStatusChoices, default=VirtualMachineStatusChoices.STATUS_ACTIVE)
    # cluster = ObjectVar(Cluster.objects)
    # tenant = ObjectVar(Tenant.objects, required=False)
    # platform = ObjectVar(Platform.objects, required=False)
    interface_name = StringVar(default="eth0")
    # mac_address = StringVar(label="MAC address", required=False)
    vcpus = IntegerVar(label="VCPUs", required=True)
    memory = IntegerVar(label="Memory (MB)", required=True)
    disk = IntegerVar(label="Disk (GB)", required=True)
    comments = TextVar(label="Comments", required=False)
    # pve_host = ObjectVar(Device.objects.filter(cluster__name='Newtelco Cluster'), label="Proxmox Host", required=True)
    PVE_DEVICES = (
        ('nt-pve', 'nt-pve'),
        ('nt-pve2', 'nt-pve2'),
        ('nt-pve5', 'nt-pve5'),
        ('nt-pve6', 'nt-pve6')
    )
    pve_host = ChoiceVar(choices=PVE_DEVICES)
    # pve_host_ip=Device.objects.filter(name=pve_host)

    def run(self, data, commit):
        pve_host=Device.objects.filter(name=data["pve_host"])
        vm = VirtualMachine(
            name=data["vm_name"],
            role=data["role"],
            status=data["status"],
            vcpus=data["vcpus"],
            memory=data["memory"],
            disk=data["disk"],
            comments=data["comments"],
        )
        if commit:
            vm.save()

        interface = Interface(
            name=data["interface_name"],
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
                    vrf=data.get("vrf"),
                )
                result = "Assigned"
            except ObjectDoesNotExist:
                a = IPAddress(
                   address=addr,
                   family=addr.version,
                   vrf=data.get("vrf"),
                )
                result = "Created"
            a.status = IPAddressStatusChoices.STATUS_ACTIVE
            a.dns_name = data["dns_name"]
            if a.interface:
                raise RuntimeError("Address %s is already assigned" % addr)
            a.interface = interface
            a.tenant = data.get("tenant")
            a.save()
            self.log_info("%s IP address %s %s" % (result, a.address, a.vrf or ""))
            setattr(vm, "primary_ip%d" % a.family, a)

        def connect_pve(addr):
            self.log_info(addr)
            proxmox = ProxmoxAPI(addr, user='root@pam',
                                         token_name='nb1', token_value='0cf6ab07-ff7e-41a3-80e4-e09e7fea6c7d', verify_ssl=False)
            self.log_success(proxmox.nodes.get())

        # self.log_info(data["pve_host"])
        pve_ip=str(pve_host.get().primary_ip4)[:-3]
        self.log_info(pve_ip)
        connect_pve(pve_ip)
        if commit:
            add_addr(data["primary_ip4"], 4)
            # add_addr(data["primary_ip6"], 6)
            vm.save()
            self.log_success("Created VM %s" % vm.name)
        else:
            self.log_success("Dry-run Success - Created VM %s" % vm.name)
