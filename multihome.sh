#!/bin/sh

DOCKER_INTERFACE="docker0"
ROUTE_TABLE_FILE="/etc/iproute2/rt_tables"
ROUTE_TABLE_NAME="multihome"

usage()
{
    echo ""
    echo "Multihome configuration script"
    echo "$0"
    echo "\t--primary-nic=<interface name>"
    echo "\t--outbound-nic=<interface name>"
    echo ""
    exit 1
}

if [ $# -eq 2 ]; then
    while [ "$1" != "" ]; do
        PARAM=`echo $1 | awk -F= '{print $1}'`
        VALUE=`echo $1 | awk -F= '{print $2}'`
        case $PARAM in
            --primary-nic)
                PRIMARY_INTERFACE=$VALUE
                ;;
            --outbound-nic)
                OUTBOUND_INTERFACE=$VALUE
                ;;
            *)
                echo "ERROR: unknown parameter \"$PARAM\""
                usage
                ;;
        esac
        shift
    done
else
    usage
fi

gather_interfaces_info()
{
    OUTBOUND_INTERFACE_IP="$(ip -4 -o addr show $OUTBOUND_INTERFACE | awk '{print $4}')"
    OUTBOUND_INTERFACE_GW="${OUTBOUND_INTERFACE_IP%.*}.1"

    PRIMARY_INTERFACE_IP="$(ip -4 -o addr show $PRIMARY_INTERFACE | awk '{print $4}')"
    PRIMARY_INTERFACE_NET="$(echo $PRIMARY_INTERFACE_IP | awk -F[./] '{print $1 "." $2 "." $3 ".0/" $5 }')"
    PRIMARY_INTERFACE_GW="${PRIMARY_INTERFACE_IP%.*}.1"

    until [ -f /sys/class/net/$DOCKER_INTERFACE/operstate ]; do
        echo "Waiting for $DOCKER_INTERFACE interface to become available"
        sleep 5
    done
    DOCKER_SUBNET="$(ip -4 -o addr show $DOCKER_INTERFACE | awk '{print $4}' | awk -F[./] '{print $1 "." $2 "." $3 ".0/" $5 }')"
}

apply_multihome_routing()
{
    if ! grep -q $ROUTE_TABLE_NAME $ROUTE_TABLE_FILE; then
        echo "Adjusting $ROUTE_TABLE_FILE file"
        echo "1 $ROUTE_TABLE_NAME" >> $ROUTE_TABLE_FILE
    fi

    ip route del dev $PRIMARY_INTERFACE
    ip route add default via $OUTBOUND_INTERFACE_GW
    ip route add default via $PRIMARY_INTERFACE_GW dev $PRIMARY_INTERFACE table $ROUTE_TABLE_NAME
    ip rule add from $PRIMARY_INTERFACE_NET table $ROUTE_TABLE_NAME
    ip rule add from $DOCKER_SUBNET lookup $ROUTE_TABLE_NAME
    ip route add $DOCKER_SUBNET dev $DOCKER_INTERFACE table $ROUTE_TABLE_NAME

    sysctl -wq net.ipv4.conf.all.rp_filter=2
}

print_output()
{
    echo "-- $ROUTE_TABLE_NAME list:"
    ip route list table $ROUTE_TABLE_NAME
    echo "-- Showing rules:"
    ip rule show
    echo "\nDone."
}

gather_interfaces_info
apply_multihome_routing
print_output
