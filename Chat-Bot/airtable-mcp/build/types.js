// Field type definitions for Airtable
export const fieldRequiresOptions = (type) => {
    switch (type) {
        case 'number':
        case 'singleSelect':
        case 'multiSelect':
        case 'date':
        case 'currency':
            return true;
        default:
            return false;
    }
};
export const getDefaultOptions = (type) => {
    switch (type) {
        case 'number':
            return { precision: 0 };
        case 'date':
            return { dateFormat: { name: 'local' } };
        case 'currency':
            return { precision: 2, symbol: '$' };
        default:
            return undefined;
    }
};
