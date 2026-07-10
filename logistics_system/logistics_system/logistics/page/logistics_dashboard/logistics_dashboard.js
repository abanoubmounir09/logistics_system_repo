frappe.pages["logistics-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Logistics Dashboard",
		single_column: true,
	});

	page.add_button("Build Run", () => open_build_run_dialog(dashboard_page), {btn_class: "btn-primary"});
	page.add_button("Refresh", () => dashboard_page.reload());

	const dashboard_page = new LogisticsDashboard(page);
	dashboard_page.reload();
};

class LogisticsDashboard {
	constructor(page) {
		this.page = page;
		this.$body = $(`
			<div class="logistics-dashboard">
				<div class="row kpi-row" style="margin: 15px 0;"></div>
				<h4>Active Delivery Runs</h4>
				<div class="active-runs-table"></div>
			</div>
		`).appendTo(page.body);
	}

	reload() {
		frappe.call({
			method: "logistics_system.api.logistics_api.dashboard_summary",
			callback: (r) => {
				if (r.message && r.message.data) {
					this.render(r.message.data);
				}
			},
		});
	}

	render(data) {
		const kpi = (label, value) => `
			<div class="col-sm-3">
				<div class="widget" style="border:1px solid var(--border-color); border-radius:8px; padding:15px; text-align:center;">
					<div style="font-size: 26px; font-weight: 600;">${value}</div>
					<div class="text-muted">${label}</div>
				</div>
			</div>`;

		this.$body.find(".kpi-row").html(
			kpi("Open Orders", data.open_orders) +
			kpi("Active Drivers", data.active_drivers) +
			kpi("Runs En Route", data.runs_en_route) +
			kpi("Cash Collected Today", format_currency(data.cash_collected_today))
		);

		let rows = data.active_runs
			.map(
				(run) => `
			<tr>
				<td><a href="/app/delivery-run/${run.name}">${run.name}</a></td>
				<td>${run.driver}</td>
				<td>${run.run_status}</td>
				<td>${format_currency(run.total_cash_collected)}</td>
			</tr>`
			)
			.join("");

		if (!rows) {
			rows = `<tr><td colspan="4" class="text-muted">No active runs</td></tr>`;
		}

		this.$body.find(".active-runs-table").html(`
			<table class="table table-bordered">
				<thead><tr><th>Run</th><th>Driver</th><th>Status</th><th>Cash Collected</th></tr></thead>
				<tbody>${rows}</tbody>
			</table>
		`);
	}
}

function open_build_run_dialog(dashboard_page) {
	const d = new frappe.ui.Dialog({
		title: "Build Delivery Run",
		fields: [
			{
				fieldname: "driver",
				fieldtype: "Link",
				options: "Driver",
				label: "Driver",
				reqd: 1,
				get_query: () => ({filters: {active: 1, status: "Available"}}),
			},
			{
				fieldname: "order_names",
				fieldtype: "MultiSelectList",
				label: "Orders (leave empty to auto-select)",
				get_data: function (txt) {
					return frappe.db.get_link_options("Order", txt, {status: "Open"});
				},
			},
		],
		primary_action_label: "Build",
		primary_action: (values) => {
			frappe.call({
				method: "logistics_system.api.logistics_api.build_delivery_run",
				args: {
					driver: values.driver,
					order_names: values.order_names && values.order_names.length ? values.order_names : null,
				},
				callback: (r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({message: r.message.message, indicator: "green"});
						d.hide();
						dashboard_page.reload();
					}
				},
			});
		},
	});
	d.show();
}
