/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * يعطّل خدمة partner_autocomplete لتفادي فشل تحميل jsvat / مكتبات خارجية
 * في بيئات بلا إنترنت. يُرجِع stubs آمنة بدل الاستدعاءات الفعلية.
 */
const disabledPartnerAutocompleteService = {
    dependencies: [],
    start() {
        return {
            autocomplete: async () => [],
            getCreateData: async () => ({}),
            isTaxIDSupported: () => false,
            getCompanyData: async () => ({}),
            validateVAT: () => false,
        };
    },
};

registry
    .category("services")
    .add("partner_autocomplete", disabledPartnerAutocompleteService, { force: true });
