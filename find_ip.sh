# A script that composes and tests an IP based on the serial number of a vehicle
# Vehicle Serial numbers are SN03101, SN03202, etc. 
# IP Addresses for vehicle DNS's are 192.168.101.100 for SN03101, 192.168.202.100 for SN03202, etc.

# Given a list of Serial Numbers, we want to find the IP address of each Vehicle's DNS and test if it is reachable

# Usage: ./find_ip.sh SN03101 SN03202 SN03303

# Loop through the list of Serial Numbers
for serial in $@
do
  # Extract the last 3 digits of the serial number
  last3=$(echo $serial | cut -c 6-8)
  # Compose the IP address
  ip="192.168.$last3.100"
  # Test if the IP is reachable
  ping -c 1 $ip > /dev/null
  if [ $? -eq 0 ]; then
    echo "Device with serial number $serial has IP address $ip and is reachable"
  else
    echo "Device with serial number $serial has IP address $ip and is not reachable"
  fi
done