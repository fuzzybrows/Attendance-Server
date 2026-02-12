import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

export const fetchMembers = createAsyncThunk('members/fetchMembers', async () => {
    const response = await axios.get('/members/');
    return response.data;
});

export const addMember = createAsyncThunk('members/addMember', async (member) => {
    const response = await axios.post('/members/', member);
    return response.data;
});

export const updateMember = createAsyncThunk('members/updateMember', async ({ id, updates }) => {
    const response = await axios.put(`/members/${id}`, updates);
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
