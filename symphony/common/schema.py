MAX_RETRIES = 50
MIN_RETRIES = 5
network = {
              "net-id": None,
              "subnet-id": None,
              "ips": None
              }
vdu = {
          "id": None,
          "network-interfaces":[],
          "mgmt-ip": None,
          "username": None,
          "password": None
          }
ns_dict = {
            "qos": None,
            "monitoring": None,
            "forwarding-graphs": {},
            "lifecycle-event": {}
            }

service_dict = {
              "nsd": ns_dict,
              "vdus":{}
              }
