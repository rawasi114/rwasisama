/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef, onMounted } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FingerSignatureField extends Component {
    static template = "simple_manufacturing.FingerSignatureField";
    static props = { ...standardFieldProps };

    setup() {
        this.canvasRef = useRef("canvas");
        this.drawing = false;
        onMounted(() => this._init());
    }

    _init() {
        const canvas = this.canvasRef.el;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = "#000000";
        this.ctx = ctx;
        const value = this.props.record.data[this.props.name];
        if (value) {
            const img = new Image();
            img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            img.src = "data:image/png;base64," + value;
        }
    }

    _pos(ev) {
        const rect = this.canvasRef.el.getBoundingClientRect();
        return {
            x: (ev.clientX - rect.left) * (this.canvasRef.el.width / rect.width),
            y: (ev.clientY - rect.top) * (this.canvasRef.el.height / rect.height),
        };
    }

    onPointerDown(ev) {
        if (this.props.readonly) {
            return;
        }
        this.drawing = true;
        const p = this._pos(ev);
        this.ctx.beginPath();
        this.ctx.moveTo(p.x, p.y);
    }

    onPointerMove(ev) {
        if (!this.drawing) {
            return;
        }
        const p = this._pos(ev);
        this.ctx.lineTo(p.x, p.y);
        this.ctx.stroke();
    }

    onPointerUp() {
        if (!this.drawing) {
            return;
        }
        this.drawing = false;
        this._save();
    }

    _save() {
        const dataUrl = this.canvasRef.el.toDataURL("image/png");
        const base64 = dataUrl.split(",")[1];
        this.props.record.update({ [this.props.name]: base64 });
    }

    clear() {
        const canvas = this.canvasRef.el;
        this.ctx.fillStyle = "#ffffff";
        this.ctx.fillRect(0, 0, canvas.width, canvas.height);
        this.props.record.update({ [this.props.name]: false });
    }
}

export const fingerSignatureField = {
    component: FingerSignatureField,
    supportedTypes: ["binary"],
};

registry.category("fields").add("finger_signature", fingerSignatureField);
