import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8001';

export const fetchSessions = createAsyncThunk('sessions/fetchSessions', async () => {
    const response = await axios.get(`${API_BASE}/sessions/`);
    return response.data;
});

export const addSession = createAsyncThunk('sessions/addSession', async (session) => {
    const response = await axios.post(`${API_BASE}/sessions/`, session);
    return response.data;
});

const sessionsSlice = createSlice({
    name: 'sessions',
    initialState: { items: [], status: 'idle', currentSession: null },
    reducers: {
        setCurrentSession: (state, action) => {
            state.currentSession = action.payload;
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchSessions.fulfilled, (state, action) => {
                state.items = action.payload;
            })
            .addCase(addSession.fulfilled, (state, action) => {
                state.items.push(action.payload);
            });
    },
});

export const { setCurrentSession } = sessionsSlice.actions;
export default sessionsSlice.reducer;
