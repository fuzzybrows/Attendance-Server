import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

export const fetchSessions = createAsyncThunk('sessions/fetchSessions', async () => {
    const response = await axios.get('/sessions/');
    return response.data;
});

export const addSession = createAsyncThunk('sessions/addSession', async (session) => {
    const response = await axios.post('/sessions/', session);
    return response.data;
});

export const deleteSession = createAsyncThunk('sessions/deleteSession', async (sessionId) => {
    await axios.delete(`/sessions/${sessionId}`);
    return sessionId;
});

export const bulkDeleteSessions = createAsyncThunk('sessions/bulkDeleteSessions', async (ids) => {
    await axios.post('/sessions/bulk-delete', { ids });
    return ids;
});

export const updateSessionStatus = createAsyncThunk('sessions/updateSessionStatus', async ({ id, status }) => {
    const response = await axios.patch(`/sessions/${id}`, { status });
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
                state.items.unshift(action.payload);
            })
            .addCase(deleteSession.fulfilled, (state, action) => {
                state.items = state.items.filter(s => s.id !== action.payload);
                if (state.currentSession?.id === action.payload) {
                    state.currentSession = null;
                }
            })
            .addCase(bulkDeleteSessions.fulfilled, (state, action) => {
                const deletedIds = new Set(action.payload);
                state.items = state.items.filter(s => !deletedIds.has(s.id));
                if (state.currentSession && deletedIds.has(state.currentSession.id)) {
                    state.currentSession = null;
                }
            })
            .addCase(updateSessionStatus.fulfilled, (state, action) => {
                const idx = state.items.findIndex(s => s.id === action.payload.id);
                if (idx !== -1) state.items[idx] = action.payload;
                if (state.currentSession?.id === action.payload.id) {
                    state.currentSession = action.payload;
                }
            });
    },
});

export const { setCurrentSession } = sessionsSlice.actions;
export default sessionsSlice.reducer;
