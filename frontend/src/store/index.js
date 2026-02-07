import { configureStore } from '@reduxjs/toolkit';
import membersReducer from './membersSlice';
import sessionsReducer from './sessionsSlice';
import attendanceReducer from './attendanceSlice';
import statsReducer from './statsSlice';

export const store = configureStore({
    reducer: {
        members: membersReducer,
        sessions: sessionsReducer,
        attendance: attendanceReducer,
        stats: statsReducer,
    },
});
