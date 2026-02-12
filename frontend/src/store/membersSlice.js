import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import logger from '../utils/logger';

export const fetchMembers = createAsyncThunk('members/fetchMembers', async () => {
    const response = await axios.get('/members/');
    return response.data;
});

export const addMember = createAsyncThunk('members/addMember', async (member) => {
    logger.info('Adding member', { type: 'member_add_attempt', email: member.email });
    const response = await axios.post('/members/', member);
    logger.info('Member added', { type: 'member_add_success', member_id: response.data.id });
    return response.data;
});

export const updateMember = createAsyncThunk('members/updateMember', async ({ id, updates }) => {
    logger.info('Updating member', { type: 'member_update_attempt', member_id: id });
    const response = await axios.put(`/members/${id}`, updates);
    logger.info('Member updated', { type: 'member_update_success', member_id: id });
    return response.data;
});

const membersSlice = createSlice({
    name: 'members',
    initialState: { items: [], status: 'idle' },
    extraReducers: (builder) => {
        builder
            .addCase(fetchMembers.fulfilled, (state, action) => {
                state.items = action.payload;
            })
            .addCase(addMember.fulfilled, (state, action) => {
                state.items.push(action.payload);
            })
            .addCase(updateMember.fulfilled, (state, action) => {
                const index = state.items.findIndex(m => m.id === action.payload.id);
                if (index !== -1) {
                    state.items[index] = action.payload;
                }
            });
    },
});

export default membersSlice.reducer;
