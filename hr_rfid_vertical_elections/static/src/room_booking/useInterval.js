/** @odoo-module **/

import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Creates an interval that will call the given callback every
 * `duration` ms.
 * @param {Function} callback
 * @param {Number} duration
 */
export function useInterval(callback, duration) {
    let interval;
    onMounted(() => (interval = setInterval(callback, duration)));
    onWillUnmount(() => clearInterval(interval));
}
