app_name = "logistics_system_repo"
app_title = "logistics_system_repo"
app_publisher = "abanoub.mounir001@gmail.com"
app_description = "logistics_system"
app_email = "abanoub.mounir001@gmail.com"
app_license = "mit"

# Permission query conditions -> restrict list views for the Driver role
permission_query_conditions = {
	"Logistics Delivery Run": "logistics_system_repo.permissions.driver_permissions.delivery_run_query_conditions",
	"Logistics Order": "logistics_system_repo.permissions.driver_permissions.order_query_conditions",
}

# Row-level permission checks -> restrict single-doc access for the Driver role
has_permission = {
	"Logistics Delivery Run": "logistics_system_repo.permissions.driver_permissions.delivery_run_has_permission",
	"Logistics Order": "logistics_system_repo.permissions.driver_permissions.order_has_permission",
}

# Fixtures: export/import Roles with the app
fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Logistics Manager", "Logistics Dispatcher", "Driver"]]]},
]

# Runs once, right after `bench install-app logistics_system_repo`
after_install = "logistics_system_repo.setup.install.after_install"