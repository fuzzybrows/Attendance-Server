import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8001';

export const fetchMembers = createAsyncThunk('members/fetchMembers', async () => {
    const response = await axios.get(`${API_BASE}/members/`);
    return response.data;
});

export const addMember = createAsyncThunk('members/addMember', async (member) => {
    const response = await axios.post(`${API_BASE}/members/`, member);
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
            });
    },
});

export default membersSlice.reducer;
