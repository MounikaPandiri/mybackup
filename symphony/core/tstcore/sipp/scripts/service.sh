instance_id=`nova list | grep -i "active" | awk -F " " '{print $2}'`
nova delete $instance_id

private=`neutron net-list | grep "20.0.0.0/24" | awk -F " " '{print $2}'`
public=`neutron net-list | grep "40.0.0.0/24" | awk -F " " '{print $2}'`
mgmt=`neutron net-list | grep "30.0.0.0/24" | awk -F " " '{print $2}'`
zop1=`neutron net-list | grep "80.0.0.0/24" | awk -F " " '{print $2}'`
#public_ext=`neutron net-list | grep "172.24.4.0/24" | awk -F " " '{print $2}'`

private_sub=`neutron subnet-list | grep "20.0.0.0/24" | awk -F " " '{print $2}'`
public_sub=`neutron subnet-list | grep "40.0.0.0/24" | awk -F " " '{print $2}'`
mgmt_sub=`neutron subnet-list | grep "30.0.0.0/24" | awk -F " " '{print $2}'`
zop1_sub=`neutron subnet-list | grep "80.0.0.0/24" | awk -F " " '{print $2}'`
#public_ext_sub=`neutron subnet-list | grep "172.24.4.0/24" | awk -F " " '{print $2}'`

router_id=`neutron router-list | grep -w "VNF_Router" | awk -F " " '{print $2}'`
neutron router-interface-delete $router_id $mgmt_sub
neutron router-interface-delete $router_id $private_sub
neutron router-interface-delete $router_id $public_sub
neutron router-interface-delete $router_id $zop1_sub
neutron router-delete $router_id

port1=`neutron port-list | grep $public_sub | awk -F " " '{print $2}'`
neutron port-delete $port1
port2=`neutron port-list | grep $private_sub | awk -F " " '{print $2}'`
neutron port-delete $port2
port3=`neutron port-list | grep $mgmt_sub | awk -F " " '{print $2}'`
neutron port-delete $port3
port4=`neutron port-list | grep $zop_sub | awk -F " " '{print $2}'`
neutron port-delete $port4
port5=`neutron port-list | grep $zop1_sub | awk -F " " '{print $2}'`
neutron port-delete $port5

neutron net-delete $private
neutron net-delete $public
neutron net-delete $mgmt
neutron net-delete $zop1

vtap=`ifconfig | grep vtap | awk -F ":" '{print $1}'`
sudo ovs-vsctl del-port $vtap

#vnfm=`ps -ax | grep "vnf-manager" | awk '{print $1}'`
vnfm=`pgrep vnf-manager`
kill $vnfm

sudo rm -rf /opt/stack/data/nova/instances/_base/*

sudo sysctl -w vm.drop_caches=3
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

mysql -u root -ptest << EOF
use heat;
delete from event;
delete from resource;
delete from stack_lock;
delete from stack;
EOF 
