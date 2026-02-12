import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = '';

export const fetchStats = createAsyncThunk('stats/fetchStats', async () => {
    const response = await axios.get(`${API_BASE}/attendance/stats`);
    return response.data;
});

export const fetchMemberStats = createAsyncThunk('stats/fetchMemberStats', async (memberId) => {
    const response = await axios.get(`${API_BASE}/statistics/member/${memberId}`);
    return response.data;
});

const statsSlice = createSlice({
    name: 'stats',
    initialState: {
        overall: [],
        memberDetail: null,
        status: 'idle'
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchStats.fulfilled, (state, action) => {
                state.overall = action.payload;
            })
            .addCase(fetchMemberStats.fulfilled, (state, action) => {
                state.memberDetail = action.payload;
            });
    },
});

export default statsSlice.reducer;
