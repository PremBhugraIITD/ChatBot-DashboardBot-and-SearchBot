import { Client } from '@sendgrid/client';
import sgMail from '@sendgrid/mail';
export class SendGridService {
    client;
    constructor(apiKey) {
        this.client = new Client();
        this.client.setApiKey(apiKey);
        sgMail.setApiKey(apiKey);
    }
    // Email Sending
    async sendEmail(params) {
        return await sgMail.send(params);
    }
    // Contact Management
    async deleteContactsByEmails(emails) {
        // First get the contact IDs for the emails
        const [searchResponse] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/contacts/search',
            body: {
                query: `email IN (${emails.map(email => `'${email}'`).join(',')})`
            }
        });
        const contacts = searchResponse.body.result || [];
        const contactIds = contacts.map(contact => contact.id).filter(id => id);
        if (contactIds.length > 0) {
            // Then delete the contacts by their IDs
            await this.client.request({
                method: 'DELETE',
                url: '/v3/marketing/contacts',
                qs: {
                    ids: contactIds.join(',')
                }
            });
        }
    }
    async listAllContacts() {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/contacts/search',
            body: {
                query: "email IS NOT NULL" // Get all contacts that have an email
            }
        });
        return response.body.result || [];
    }
    async addContact(contact) {
        const [response] = await this.client.request({
            method: 'PUT',
            url: '/v3/marketing/contacts',
            body: {
                contacts: [contact]
            }
        });
        return response;
    }
    async getContactsByList(listId) {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/contacts/search',
            body: {
                query: `CONTAINS(list_ids, '${listId}')`
            }
        });
        return response.body.result || [];
    }
    async getList(listId) {
        const [response] = await this.client.request({
            method: 'GET',
            url: `/v3/marketing/lists/${listId}`
        });
        return response.body;
    }
    async listContactLists() {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/marketing/lists'
        });
        return response.body.result;
    }
    async deleteList(listId) {
        await this.client.request({
            method: 'DELETE',
            url: `/v3/marketing/lists/${listId}`
        });
    }
    async createList(name) {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/lists',
            body: { name }
        });
        return response.body;
    }
    async addContactsToList(listId, contactEmails) {
        const [response] = await this.client.request({
            method: 'PUT',
            url: '/v3/marketing/contacts',
            body: {
                list_ids: [listId],
                contacts: contactEmails.map(email => ({ email }))
            }
        });
        return response;
    }
    async removeContactsFromList(listId, contactEmails) {
        // First get the contact IDs for the emails
        const [searchResponse] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/contacts/search',
            body: {
                query: `email IN (${contactEmails.map(email => `'${email}'`).join(',')}) AND CONTAINS(list_ids, '${listId}')`
            }
        });
        const contacts = searchResponse.body.result || [];
        const contactIds = contacts.map(contact => contact.id).filter(id => id);
        if (contactIds.length > 0) {
            // Remove the contacts from the list
            await this.client.request({
                method: 'DELETE',
                url: `/v3/marketing/lists/${listId}/contacts`,
                qs: {
                    contact_ids: contactIds.join(',')
                }
            });
        }
    }
    // Template Management
    async createTemplate(params) {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/templates',
            body: {
                name: params.name,
                generation: 'dynamic'
            }
        });
        const templateId = response.body.id;
        // Create the first version of the template
        const [versionResponse] = await this.client.request({
            method: 'POST',
            url: `/v3/templates/${templateId}/versions`,
            body: {
                template_id: templateId,
                name: `${params.name} v1`,
                subject: params.subject,
                html_content: params.html_content,
                plain_content: params.plain_content,
                active: 1
            }
        });
        return {
            id: templateId,
            name: params.name,
            generation: 'dynamic',
            updated_at: new Date().toISOString(),
            versions: [{
                    id: versionResponse.body.id,
                    template_id: templateId,
                    active: 1,
                    name: `${params.name} v1`,
                    html_content: params.html_content,
                    plain_content: params.plain_content,
                    subject: params.subject
                }]
        };
    }
    async listTemplates() {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/templates',
            qs: {
                generations: 'dynamic'
            }
        });
        return (response.body.templates || []);
    }
    async getTemplate(templateId) {
        const [response] = await this.client.request({
            method: 'GET',
            url: `/v3/templates/${templateId}`
        });
        return response.body;
    }
    async deleteTemplate(templateId) {
        await this.client.request({
            method: 'DELETE',
            url: `/v3/templates/${templateId}`
        });
    }
    // Email Validation
    async validateEmail(email) {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/validations/email',
            body: { email }
        });
        return response.body;
    }
    // Statistics
    async getStats(params) {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/stats',
            qs: params
        });
        return response.body;
    }
    // Single Sends (New Marketing Campaigns API)
    async createSingleSend(params) {
        const [response] = await this.client.request({
            method: 'POST',
            url: '/v3/marketing/singlesends',
            body: params
        });
        return response.body;
    }
    async scheduleSingleSend(singleSendId, sendAt) {
        const [response] = await this.client.request({
            method: 'PUT',
            url: `/v3/marketing/singlesends/${singleSendId}/schedule`,
            body: {
                send_at: sendAt
            }
        });
        return response.body;
    }
    async getSingleSend(singleSendId) {
        const [response] = await this.client.request({
            method: 'GET',
            url: `/v3/marketing/singlesends/${singleSendId}`
        });
        return response.body;
    }
    async listSingleSends() {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/marketing/singlesends'
        });
        return response.body.result || [];
    }
    // Suppression Groups
    async getSuppressionGroups() {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/asm/groups'
        });
        return response.body;
    }
    // Verified Senders
    async getVerifiedSenders() {
        const [response] = await this.client.request({
            method: 'GET',
            url: '/v3/verified_senders'
        });
        return response.body;
    }
}
