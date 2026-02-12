import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import logger from '../utils/logger';

export const login = createAsyncThunk('auth/login', async (credentials, { rejectWithValue }) => {
    try {
        logger.info('Login attempt', { type: 'login_attempt', login: credentials.login });
        const response = await axios.post('/auth/login', credentials);
        logger.info('Login successful', { type: 'login_success', login: credentials.login });
        return response.data;
    } catch (err) {
        logger.warn('Login failed', { type: 'login_failed', login: credentials.login, error: err.message });
        return rejectWithValue(err.response?.data || { detail: 'Network error' });
    }
});

export const verifyOTP = createAsyncThunk('auth/verifyOTP', async (data, { rejectWithValue }) => {
    try {
        logger.info('Verifying OTP', { type: 'otp_verification_attempt', login: data.login });
        const response = await axios.post('/auth/verify-otp', data);
        logger.info('OTP Verified', { type: 'otp_verification_success', login: data.login });
        return response.data;
    } catch (err) {
        logger.warn('OTP Verification failed', { type: 'otp_verification_failed', login: data.login, error: err.message });
        return rejectWithValue(err.response?.data || { detail: 'Network error' });
    }
});


const authSlice = createSlice({
    name: 'auth',
    initialState: {
        user: JSON.parse(localStorage.getItem('user')) || null,
        token: localStorage.getItem('token') || null,
        loading: false,
        error: null,
        needsVerification: null // { method, login }
    },
    reducers: {
        logout: (state) => {
            state.user = null;
            state.token = null;
            state.needsVerification = null;
            localStorage.removeItem('user');
            localStorage.removeItem('token');
        },
        clearError: (state) => {
            state.error = null;
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(login.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.needsVerification = null;
            })
            .addCase(login.fulfilled, (state, action) => {
                state.loading = false;
                if (action.payload.status === 'unverified') {
                    state.needsVerification = {
                        method: action.payload.method,
                        login: action.meta.arg.login
                    };
                } else {
                    state.user = action.payload.member;
                    state.token = action.payload.access_token;
                    localStorage.setItem('user', JSON.stringify(action.payload.member));
                    localStorage.setItem('token', action.payload.access_token);
                }
            })
            .addCase(login.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload?.detail || 'Login failed';
            })
            .addCase(verifyOTP.fulfilled, (state, action) => {
                state.user = action.payload.member;
                state.token = action.payload.access_token;
                state.needsVerification = null;
                localStorage.setItem('user', JSON.stringify(action.payload.member));
                localStorage.setItem('token', action.payload.access_token);
            })
            .addCase(verifyOTP.rejected, (state, action) => {
                state.error = action.payload?.detail || 'Verification failed';
            });
    }
});

export const { logout, clearError } = authSlice.actions;
export default authSlice.reducer;
