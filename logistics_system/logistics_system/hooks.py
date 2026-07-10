app_name = "logistics_system"
app_title = "Logistics System"
app_publisher = "Backend Task Submission"
app_description = "Delivery orders, delivery runs, drivers, and cash banking for a logistics operation."
app_email = "dev@example.com"
app_license = "MIT"

# Permission query conditions -> restrict list views for the Driver role
permission_query_conditions = {
	"Delivery Run": "logistics_system.permissions.driver_permissions.delivery_run_query_conditions",
	"Order": "logistics_system.permissions.driver_permissions.order_query_conditions",
}

# Row-level permission checks -> restrict single-doc access for the Driver role
has_permission = {
	"Delivery Run": "logistics_system.permissions.driver_permissions.delivery_run_has_permission",
	"Order": "logistics_system.permissions.driver_permissions.order_has_permission",
}

# Fixtures: export/import Roles with the app
fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Logistics Manager", "Logistics Dispatcher", "Driver"]]]},
]

# Runs once, right after `bench install-app logistics_system`
after_install = "logistics_system.setup.install.after_install"
