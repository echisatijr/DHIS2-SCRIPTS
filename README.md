# DHIS2-SCRIPTS
-->Scripts to help in the management of DHIS2 servers

get_CA_under_a_district.py
-->This scripts allows you to pull all the Catchments areas (Level 5) in a district with their correponding
   healthy facility (Level 4) as a parent.
-->Saves the data in a file "{District_name}_CA.xlsx".

user_creation.py
-->This script allows you to create users.
-->It get details of a user from a file "{District_name}_users.xlsx.
-->It get details about a an organisation unit from the file created by the "get_CA_under_a_district.py".