import { McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
export function validateString(value, field) {
    if (typeof value !== 'string') {
        throw new McpError(ErrorCode.InvalidParams, `${field} must be a string`);
    }
    return value;
}
export function validateOptionalString(value) {
    if (value === undefined)
        return undefined;
    return validateString(value, 'value');
}
export function validateNumber(value, field) {
    if (typeof value !== 'number') {
        throw new McpError(ErrorCode.InvalidParams, `${field} must be a number`);
    }
    return value;
}
export function validateOptionalNumber(value) {
    if (value === undefined)
        return undefined;
    return validateNumber(value, 'value');
}
export function validateStringArray(value) {
    if (!Array.isArray(value) || !value.every(item => typeof item === 'string')) {
        throw new McpError(ErrorCode.InvalidParams, 'Value must be an array of strings');
    }
    return value;
}
export function validateOptionalStringArray(value) {
    if (value === undefined)
        return undefined;
    return validateStringArray(value);
}
export function validateGetCardsListRequest(args) {
    if (!args.listId) {
        throw new McpError(ErrorCode.InvalidParams, 'listId is required');
    }
    return {
        listId: validateString(args.listId, 'listId'),
    };
}
export function validateGetRecentActivityRequest(args) {
    return {
        limit: validateOptionalNumber(args.limit),
    };
}
export function validateAddCardRequest(args) {
    if (!args.listId || !args.name) {
        throw new McpError(ErrorCode.InvalidParams, 'listId and name are required');
    }
    return {
        listId: validateString(args.listId, 'listId'),
        name: validateString(args.name, 'name'),
        description: validateOptionalString(args.description),
        dueDate: validateOptionalString(args.dueDate),
        labels: validateOptionalStringArray(args.labels),
    };
}
export function validateUpdateCardRequest(args) {
    if (!args.cardId) {
        throw new McpError(ErrorCode.InvalidParams, 'cardId is required');
    }
    return {
        cardId: validateString(args.cardId, 'cardId'),
        name: validateOptionalString(args.name),
        description: validateOptionalString(args.description),
        dueDate: validateOptionalString(args.dueDate),
        labels: validateOptionalStringArray(args.labels),
    };
}
export function validateArchiveCardRequest(args) {
    if (!args.cardId) {
        throw new McpError(ErrorCode.InvalidParams, 'cardId is required');
    }
    return {
        cardId: validateString(args.cardId, 'cardId'),
    };
}
export function validateAddListRequest(args) {
    if (!args.name) {
        throw new McpError(ErrorCode.InvalidParams, 'name is required');
    }
    return {
        name: validateString(args.name, 'name'),
    };
}
export function validateArchiveListRequest(args) {
    if (!args.listId) {
        throw new McpError(ErrorCode.InvalidParams, 'listId is required');
    }
    return {
        listId: validateString(args.listId, 'listId'),
    };
}
export function validateMoveCardRequest(args) {
    if (!args.cardId || !args.listId) {
        throw new McpError(ErrorCode.InvalidParams, 'cardId and listId are required');
    }
    return {
        cardId: validateString(args.cardId, 'cardId'),
        listId: validateString(args.listId, 'listId'),
    };
}
export function validateAttachImageRequest(args) {
    if (!args.cardId || !args.imageUrl) {
        throw new McpError(ErrorCode.InvalidParams, 'cardId and imageUrl are required');
    }
    // Validate image URL format
    const imageUrl = validateString(args.imageUrl, 'imageUrl');
    try {
        new URL(imageUrl);
    }
    catch (e) {
        throw new McpError(ErrorCode.InvalidParams, 'imageUrl must be a valid URL');
    }
    return {
        cardId: validateString(args.cardId, 'cardId'),
        imageUrl: imageUrl,
        name: validateOptionalString(args.name),
    };
}
export function validateSetActiveBoardRequest(args) {
    if (!args.boardId) {
        throw new McpError(ErrorCode.InvalidParams, 'boardId is required');
    }
    return {
        boardId: validateString(args.boardId, 'boardId'),
    };
}
export function validateSetActiveWorkspaceRequest(args) {
    if (!args.workspaceId) {
        throw new McpError(ErrorCode.InvalidParams, 'workspaceId is required');
    }
    return {
        workspaceId: validateString(args.workspaceId, 'workspaceId'),
    };
}
export function validateListBoardsInWorkspaceRequest(args) {
    if (!args.workspaceId) {
        throw new McpError(ErrorCode.InvalidParams, 'workspaceId is required');
    }
    return {
        workspaceId: validateString(args.workspaceId, 'workspaceId'),
    };
}
//# sourceMappingURL=validators.js.map