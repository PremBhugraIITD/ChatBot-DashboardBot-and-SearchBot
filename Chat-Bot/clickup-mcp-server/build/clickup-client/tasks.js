export class TasksClient {
    constructor(client) {
        this.client = client;
    }
    /**
     * Get tasks from a specific list
     * @param listId The ID of the list to get tasks from
     * @param params Optional parameters for filtering tasks
     * @returns A list of tasks
     */
    async getTasksFromList(listId, params) {
        return this.client.get(`/list/${listId}/task`, params);
    }
    // Removed pseudo endpoints for getting tasks from spaces and folders
    /**
     * Get a specific task by ID
     * @param taskId The ID of the task to get
     * @param params Optional parameters (include_subtasks)
     * @returns The task details
     */
    async getTask(taskId, params) {
        return this.client.get(`/task/${taskId}`, params);
    }
    /**
     * Create a new task in a list
     * @param listId The ID of the list to create the task in
     * @param params The task parameters
     * @returns The created task
     */
    async createTask(listId, params) {
        return this.client.post(`/list/${listId}/task`, params);
    }
    /**
     * Update an existing task
     * @param taskId The ID of the task to update
     * @param params The task parameters to update
     * @returns The updated task
     */
    async updateTask(taskId, params) {
        return this.client.put(`/task/${taskId}`, params);
    }
    /**
     * Delete a task
     * @param taskId The ID of the task to delete
     * @returns Success message
     */
    async deleteTask(taskId) {
        return this.client.delete(`/task/${taskId}`);
    }
    /**
     * Get subtasks of a specific task
     * @param taskId The ID of the task to get subtasks for
     * @returns A list of subtasks
     */
    async getSubtasks(taskId) {
        try {
            // First, we need to get the task to find its list ID
            const task = await this.getTask(taskId);
            if (!task.list || !task.list.id) {
                throw new Error('Task does not have a list ID');
            }
            // Then, get all tasks from the list with subtasks included
            const result = await this.getTasksFromList(task.list.id, { subtasks: true });
            // Filter tasks to find those that have the specified task as parent
            return result.tasks.filter(task => task.parent === taskId);
        }
        catch (error) {
            console.error(`Error getting subtasks for task ${taskId}:`, error);
            return [];
        }
    }
}
export const createTasksClient = (client) => {
    return new TasksClient(client);
};
//# sourceMappingURL=tasks.js.map