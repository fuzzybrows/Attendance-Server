import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = '';

export const fetchAttendance = createAsyncThunk('attendance/fetchAttendance', async (sessionId) => {
    const response = await axios.get(`${API_BASE}/attendance/session/${sessionId}`);
    console.log('fetchAttendance response:', response.data);
    return response.data;
});

export const submitAttendance = createAsyncThunk('attendance/submitAttendance', async (data) => {
    const response = await axios.post(`${API_BASE}/attendance/`, data);
    return response.data;
});

export const deleteAttendance = createAsyncThunk('attendance/deleteAttendance', async (attendanceId) => {
    await axios.delete(`${API_BASE}/attendance/${attendanceId}`);
    return attendanceId;
});

export const bulkDeleteAttendance = createAsyncThunk('attendance/bulkDeleteAttendance', async (ids) => {
    await axios.post(`${API_BASE}/attendance/bulk-delete`, { ids });
    return ids;
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
            })
            .addCase(deleteAttendance.fulfilled, (state, action) => {
                state.items = state.items.filter(a => a.id !== action.payload);
            })
            .addCase(bulkDeleteAttendance.fulfilled, (state, action) => {
                const deletedIds = new Set(action.payload);
                state.items = state.items.filter(a => !deletedIds.has(a.id));
            });
    },
});

export default attendanceSlice.reducer;
