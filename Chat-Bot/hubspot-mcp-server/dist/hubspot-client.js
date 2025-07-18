import { Client } from '@hubspot/api-client';
import dotenv from 'dotenv';
dotenv.config();
// Convert any datetime objects to ISO strings
export function convertDatetimeFields(obj) {
    if (obj === null || obj === undefined) {
        return obj;
    }
    if (typeof obj === 'object') {
        if (obj instanceof Date) {
            return obj.toISOString();
        }
        if (Array.isArray(obj)) {
            return obj.map(item => convertDatetimeFields(item));
        }
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
            result[key] = convertDatetimeFields(value);
        }
        return result;
    }
    return obj;
}
export class HubSpotClient {
    client;
    constructor(accessToken) {
        const token = accessToken || process.env.HUBSPOT_ACCESS_TOKEN;
        if (!token) {
            throw new Error('HUBSPOT_ACCESS_TOKEN environment variable is required');
        }
        this.client = new Client({ accessToken: token });
    }
    async getRecentCompanies(limit = 10) {
        try {
            // Create search request with sort by lastmodifieddate
            const searchRequest = {
                sorts: ['lastmodifieddate:desc'],
                limit,
                properties: ['name', 'domain', 'website', 'phone', 'industry', 'hs_lastmodifieddate']
            };
            // Execute the search
            const searchResponse = await this.client.crm.companies.searchApi.doSearch(searchRequest);
            // Convert the response to a dictionary
            const companiesDict = searchResponse.results;
            return convertDatetimeFields(companiesDict);
        }
        catch (error) {
            console.error('Error getting recent companies:', error);
            return { error: error.message };
        }
    }
    async getRecentContacts(limit = 10) {
        try {
            // Create search request with sort by lastmodifieddate
            const searchRequest = {
                sorts: ['lastmodifieddate:desc'],
                limit,
                properties: ['firstname', 'lastname', 'email', 'phone', 'company', 'hs_lastmodifieddate', 'lastmodifieddate']
            };
            // Execute the search
            const searchResponse = await this.client.crm.contacts.searchApi.doSearch(searchRequest);
            // Convert the response to a dictionary
            const contactsDict = searchResponse.results;
            return convertDatetimeFields(contactsDict);
        }
        catch (error) {
            console.error('Error getting recent contacts:', error);
            return { error: error.message };
        }
    }
    async getCompanyActivity(companyId) {
        try {
            // Step 1: Get all engagement IDs associated with the company using CRM Associations v4 API
            const associatedEngagements = await this.client.crm.associations.v4.basicApi.getPage('companies', companyId, 'engagements', undefined, 500);
            // Extract engagement IDs from the associations response
            const engagementIds = [];
            if (associatedEngagements.results) {
                for (const result of associatedEngagements.results) {
                    engagementIds.push(result.toObjectId);
                }
            }
            // Step 2: Get detailed information for each engagement
            const activities = [];
            for (const engagementId of engagementIds) {
                const engagementResponse = await this.client.apiRequest({
                    method: 'GET',
                    path: `/engagements/v1/engagements/${engagementId}`
                });
                // Ensure we have a proper response body
                const responseBody = engagementResponse.body;
                const engagementData = responseBody.engagement || {};
                const metadata = responseBody.metadata || {};
                // Format the engagement
                const formattedEngagement = {
                    id: engagementData.id,
                    type: engagementData.type,
                    created_at: engagementData.createdAt,
                    last_updated: engagementData.lastUpdated,
                    created_by: engagementData.createdBy,
                    modified_by: engagementData.modifiedBy,
                    timestamp: engagementData.timestamp,
                    associations: engagementResponse.body.associations || {}
                };
                // Add type-specific metadata formatting
                if (engagementData.type === 'NOTE') {
                    formattedEngagement.content = metadata.body || '';
                }
                else if (engagementData.type === 'EMAIL') {
                    formattedEngagement.content = {
                        subject: metadata.subject || '',
                        from: {
                            raw: metadata.from?.raw || '',
                            email: metadata.from?.email || '',
                            firstName: metadata.from?.firstName || '',
                            lastName: metadata.from?.lastName || ''
                        },
                        to: (metadata.to || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        cc: (metadata.cc || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        bcc: (metadata.bcc || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        sender: {
                            email: metadata.sender?.email || ''
                        },
                        body: metadata.text || metadata.html || ''
                    };
                }
                else if (engagementData.type === 'TASK') {
                    formattedEngagement.content = {
                        subject: metadata.subject || '',
                        body: metadata.body || '',
                        status: metadata.status || '',
                        for_object_type: metadata.forObjectType || ''
                    };
                }
                else if (engagementData.type === 'MEETING') {
                    formattedEngagement.content = {
                        title: metadata.title || '',
                        body: metadata.body || '',
                        start_time: metadata.startTime,
                        end_time: metadata.endTime,
                        internal_notes: metadata.internalMeetingNotes || ''
                    };
                }
                else if (engagementData.type === 'CALL') {
                    formattedEngagement.content = {
                        body: metadata.body || '',
                        from_number: metadata.fromNumber || '',
                        to_number: metadata.toNumber || '',
                        duration_ms: metadata.durationMilliseconds,
                        status: metadata.status || '',
                        disposition: metadata.disposition || ''
                    };
                }
                activities.push(formattedEngagement);
            }
            // Convert any datetime fields and return
            return convertDatetimeFields(activities);
        }
        catch (error) {
            console.error('Error getting company activity:', error);
            return { error: error.message };
        }
    }
    async getRecentEngagements(days = 7, limit = 50) {
        try {
            // Calculate the date range (past N days)
            const endTime = new Date();
            const startTime = new Date(endTime);
            startTime.setDate(startTime.getDate() - days);
            // Format timestamps for API call
            const startTimestamp = Math.floor(startTime.getTime());
            const endTimestamp = Math.floor(endTime.getTime());
            // Get all recent engagements
            const engagementsResponse = await this.client.apiRequest({
                method: 'GET',
                path: '/engagements/v1/engagements/recent/modified',
                qs: {
                    count: limit,
                    since: startTimestamp,
                    offset: 0
                }
            });
            // Format the engagements similar to company_activity
            const formattedEngagements = [];
            // Ensure we have a proper response body
            const responseBody = engagementsResponse.body;
            for (const engagement of responseBody.results || []) {
                const engagementData = engagement.engagement || {};
                const metadata = engagement.metadata || {};
                const formattedEngagement = {
                    id: engagementData.id,
                    type: engagementData.type,
                    created_at: engagementData.createdAt,
                    last_updated: engagementData.lastUpdated,
                    created_by: engagementData.createdBy,
                    modified_by: engagementData.modifiedBy,
                    timestamp: engagementData.timestamp,
                    associations: engagement.associations || {}
                };
                // Add type-specific metadata formatting identical to company_activity
                if (engagementData.type === 'NOTE') {
                    formattedEngagement.content = metadata.body || '';
                }
                else if (engagementData.type === 'EMAIL') {
                    formattedEngagement.content = {
                        subject: metadata.subject || '',
                        from: {
                            raw: metadata.from?.raw || '',
                            email: metadata.from?.email || '',
                            firstName: metadata.from?.firstName || '',
                            lastName: metadata.from?.lastName || ''
                        },
                        to: (metadata.to || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        cc: (metadata.cc || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        bcc: (metadata.bcc || []).map((recipient) => ({
                            raw: recipient.raw || '',
                            email: recipient.email || '',
                            firstName: recipient.firstName || '',
                            lastName: recipient.lastName || ''
                        })),
                        sender: {
                            email: metadata.sender?.email || ''
                        },
                        body: metadata.text || metadata.html || ''
                    };
                }
                else if (engagementData.type === 'TASK') {
                    formattedEngagement.content = {
                        subject: metadata.subject || '',
                        body: metadata.body || '',
                        status: metadata.status || '',
                        for_object_type: metadata.forObjectType || ''
                    };
                }
                else if (engagementData.type === 'MEETING') {
                    formattedEngagement.content = {
                        title: metadata.title || '',
                        body: metadata.body || '',
                        start_time: metadata.startTime,
                        end_time: metadata.endTime,
                        internal_notes: metadata.internalMeetingNotes || ''
                    };
                }
                else if (engagementData.type === 'CALL') {
                    formattedEngagement.content = {
                        body: metadata.body || '',
                        from_number: metadata.fromNumber || '',
                        to_number: metadata.toNumber || '',
                        duration_ms: metadata.durationMilliseconds,
                        status: metadata.status || '',
                        disposition: metadata.disposition || ''
                    };
                }
                formattedEngagements.push(formattedEngagement);
            }
            // Convert any datetime fields and return
            return convertDatetimeFields(formattedEngagements);
        }
        catch (error) {
            console.error('Error getting recent engagements:', error);
            return { error: error.message };
        }
    }
    async createContact(firstname, lastname, email, properties) {
        try {
            // Search for existing contacts with same name and company
            const company = properties?.company;
            // Use type assertion to satisfy the HubSpot API client types
            const searchRequest = {
                filterGroups: [{
                        filters: [
                            {
                                propertyName: 'firstname',
                                operator: 'EQ',
                                value: firstname
                            },
                            {
                                propertyName: 'lastname',
                                operator: 'EQ',
                                value: lastname
                            }
                        ]
                    }]
            };
            // Add company filter if provided
            if (company) {
                searchRequest.filterGroups[0].filters.push({
                    propertyName: 'company',
                    operator: 'EQ',
                    value: company
                });
            }
            const searchResponse = await this.client.crm.contacts.searchApi.doSearch(searchRequest);
            if (searchResponse.total > 0) {
                // Contact already exists
                return {
                    message: 'Contact already exists',
                    contact: searchResponse.results[0]
                };
            }
            // If no existing contact found, proceed with creation
            const contactProperties = {
                firstname,
                lastname
            };
            // Add email if provided
            if (email) {
                contactProperties.email = email;
            }
            // Add any additional properties
            if (properties) {
                Object.assign(contactProperties, properties);
            }
            // Create contact
            const apiResponse = await this.client.crm.contacts.basicApi.create({
                properties: contactProperties
            });
            return apiResponse;
        }
        catch (error) {
            console.error('Error creating contact:', error);
            throw new Error(`HubSpot API error: ${error.message}`);
        }
    }
    async createCompany(name, properties) {
        try {
            // Search for existing companies with same name
            // Use type assertion to satisfy the HubSpot API client types
            const searchRequest = {
                filterGroups: [{
                        filters: [
                            {
                                propertyName: 'name',
                                operator: 'EQ',
                                value: name
                            }
                        ]
                    }]
            };
            const searchResponse = await this.client.crm.companies.searchApi.doSearch(searchRequest);
            if (searchResponse.total > 0) {
                // Company already exists
                return {
                    message: 'Company already exists',
                    company: searchResponse.results[0]
                };
            }
            // If no existing company found, proceed with creation
            const companyProperties = {
                name
            };
            // Add any additional properties
            if (properties) {
                Object.assign(companyProperties, properties);
            }
            // Create company
            const apiResponse = await this.client.crm.companies.basicApi.create({
                properties: companyProperties
            });
            return apiResponse;
        }
        catch (error) {
            console.error('Error creating company:', error);
            throw new Error(`HubSpot API error: ${error.message}`);
        }
    }
    async updateContact(contactId, properties) {
        try {
            // Check if contact exists
            try {
                await this.client.crm.contacts.basicApi.getById(contactId);
            }
            catch (error) {
                // If contact doesn't exist, return a message
                if (error.statusCode === 404) {
                    return {
                        message: 'Contact not found, no update performed',
                        contactId
                    };
                }
                // For other errors, throw them to be caught by the outer try/catch
                throw error;
            }
            // Update the contact
            const apiResponse = await this.client.crm.contacts.basicApi.update(contactId, {
                properties
            });
            return {
                message: 'Contact updated successfully',
                contactId,
                properties
            };
        }
        catch (error) {
            console.error('Error updating contact:', error);
            throw new Error(`HubSpot API error: ${error.message}`);
        }
    }
    async updateCompany(companyId, properties) {
        try {
            // Check if company exists
            try {
                await this.client.crm.companies.basicApi.getById(companyId);
            }
            catch (error) {
                // If company doesn't exist, return a message
                if (error.statusCode === 404) {
                    return {
                        message: 'Company not found, no update performed',
                        companyId
                    };
                }
                // For other errors, throw them to be caught by the outer try/catch
                throw error;
            }
            // Update the company
            const apiResponse = await this.client.crm.companies.basicApi.update(companyId, {
                properties
            });
            return {
                message: 'Company updated successfully',
                companyId,
                properties
            };
        }
        catch (error) {
            console.error('Error updating company:', error);
            throw new Error(`HubSpot API error: ${error.message}`);
        }
    }
}
//# sourceMappingURL=hubspot-client.js.map