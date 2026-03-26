/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class WebsiteDashboardAction extends Component {
    static template = "x_180dc_website_content.WebsiteDashboardAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: null,
            payload: null,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.payload = await this.orm.call("x_180dc.website.settings", "x_180dc_dashboard_payload", []);
        } catch (error) {
            this.state.error = error.message || "Unable to load website dashboard.";
            this.notification.add(this.state.error, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async reload() {
        await this.loadDashboard();
    }

    openAction(actionXmlId) {
        return this.action.doAction(actionXmlId);
    }
}

registry.category("actions").add("x_180dc_website_dashboard", WebsiteDashboardAction);
