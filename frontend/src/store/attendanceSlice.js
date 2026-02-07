import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8001';

export const fetchAttendance = createAsyncThunk('attendance/fetchAttendance', async (sessionId) => {
    const response = await axios.get(`${API_BASE}/attendance/${sessionId}`);
    return response.data;
});

export const submitAttendance = createAsyncThunk('attendance/submitAttendance', async (data) => {
    const response = await axios.post(`${API_BASE}/attendance/`, data);
    return response.data;
});

const attendanceSlice = createSlice({
    name: 'attendance',
    initialState: { items: [], status: 'idle' },
    extraReducers: (builder) => {
        builder
            .addCase(fetchAttendance.fulfilled, (state, action) => {
                state.items = action.payload;
            })
            .addCase(submitAttendance.fulfilled, (state, action) => {
                state.items.push(action.payload);
            });
    },
});

export default attendanceSlice.reducer;
