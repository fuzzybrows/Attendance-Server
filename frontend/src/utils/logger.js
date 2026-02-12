const getTimestamp = () => new Date().toISOString();

const formatLog = (level, message, extra = {}) => {
    const { type = 'generic_log', ...restExtra } = extra;
    const logRecord = {
        timestamp: getTimestamp(),
        level,
        message,
        logger: 'frontend',
        type,
        ...restExtra
    };
    return JSON.stringify(logRecord);
};

const logger = {
    info: (message, extra) => console.info(formatLog('INFO', message, extra)),
    warn: (message, extra) => console.warn(formatLog('WARNING', message, extra)),
    error: (message, extra) => console.error(formatLog('ERROR', message, extra)),
    debug: (message, extra) => console.debug(formatLog('DEBUG', message, extra)),
};

export default logger;
