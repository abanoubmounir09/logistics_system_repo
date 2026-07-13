// Copyright (c) 2026, abanoub.mounir001@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Logistics Delivery Run", {
    refresh(frm) {
        frm.events.manual_build_run(frm)
        frm.events.add_start_run_button(frm)
        frm.events.stop_deliverd(frm)
        
    },
	before_save(frm) {
        frm.events.validate_delivery_stops(frm)
	},
    validate_delivery_stops:function(frm){
        console.log("Validating delivery stops...");
        if(frm.doc.delivery_stops.length == 0){
            frappe.msgprint(__("Please add at least one delivery stop."));
            frappe.validated = false;
        }else {
			frappe.validated = true;
		}
    },
    manual_build_run: function(frm) {
        frm.events.validate_delivery_stops(frm)
        if(frm.doc.run_status == "Draft"){ 
        frm.add_custom_button(__('Build Delivery Run'), function() {
            frm.events.build_run_manual(frm);
        },"actions");
     }
    },
    add_start_run_button: function(frm) {
        if(frm.doc.run_status == "Assigned"){ 
        frm.add_custom_button(__('Start Delivery Run'), function() {
            frm.events.start_delivery_run(frm);
        },"actions");
     }
    },
    build_run_manual(frm) {
            frappe.call({
                method: "manual_build_run",
                doc:frm.doc,
                args: {
                    driver: frm.doc.driver,
                    order_names: frm.doc.delivery_stops.map(s => s.related_order)
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(__("Delivery Run started successfully."));
                        frm.refresh();
                    }
                }
            },);
    },
    start_delivery_run(frm) {
        frappe.call({
            method: "start_run",
            doc:frm.doc,
            callback: function (r) {
                if (r.message) {
                    frappe.msgprint(__("Start Run started successfully."));
                    frm.refresh();
                        }
                    }
                },);
        },
    stop_deliverd(frm) {
        if(frm.doc.run_status=="En Route"){ 
            frm.add_custom_button(__('Stop Deliverd'), function() {
                frappe.prompt(
                    {
                        label: "Order",
                        fieldname: "order_name",
                        fieldtype: "Link",
                        options: "Logistics Order",              // ✅ Logistics Order is a real standalone DocType
                        reqd: 1,
                        get_query: () => ({ filters: { status: "En Route" ,"assigned_driver":frm.doc.driver} }),   // optional: only show Open orders
                    },
                     ( values ) =>{
                        console.log(values)
                    frappe.call({
                        method: "mark_stop_delivered",
                        doc:frm.doc,
                        args:{
                            "related_order": values.order_name
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__("Order Deliverd successfully With updated Cash."));
                                frm.refresh();
                                    }
                                }
                            },);
                })
            },"actions");
        
        }
    }

});
