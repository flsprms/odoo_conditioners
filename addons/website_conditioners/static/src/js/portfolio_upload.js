/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";
import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

/**
 * Standard FileInput posts every selected file in one request. A large album
 * then hits nginx/Odoo limits and the UI gets HTML instead of JSON.
 * Upload one file per request so dozens of photos still work.
 */
export class SequentialFileInput extends FileInput {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async onFileInputChange() {
        this.state.isDisable = true;
        try {
            const files = [...this.fileInputRef.el.files];
            if (!files.length) {
                return;
            }
            const allParsed = [];
            for (const file of files) {
                const httpParams = {
                    csrf_token: odoo.csrf_token,
                    ufile: [file],
                };
                const { resId, resModel } = this.props;
                if (resModel) {
                    httpParams.model = resModel;
                }
                if (resId !== undefined) {
                    httpParams.id = resId;
                }
                let parsedFileData;
                try {
                    parsedFileData = await this.uploadFiles(this.props.route, httpParams);
                } catch (error) {
                    this.notification.add(
                        _t(
                            "Не удалось загрузить «%(name)s». Попробуйте меньше файлов за раз или снимки меньшего размера.",
                            { name: file.name }
                        ),
                        { title: _t("Ошибка загрузки"), type: "danger" }
                    );
                    throw error;
                }
                if (parsedFileData) {
                    allParsed.push(...parsedFileData);
                }
            }
            this.props.onUpload(allParsed, files);
            this.fileInputRef.el.value = null;
        } finally {
            this.state.isDisable = false;
        }
    }
}

export class PortfolioMany2ManyBinaryField extends Many2ManyBinaryField {
    static components = {
        ...Many2ManyBinaryField.components,
        FileInput: SequentialFileInput,
    };
}

export const portfolioMany2ManyBinaryField = {
    ...many2ManyBinaryField,
    component: PortfolioMany2ManyBinaryField,
};

registry.category("fields").add("portfolio_many2many_binary", portfolioMany2ManyBinaryField);
