USE event_booking_db;

-- Check and add attendee_name
SELECT COUNT(*) INTO @name_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'event_booking_db' 
AND TABLE_NAME = 'bookings' 
AND COLUMN_NAME = 'attendee_name';

SET @sql = IF(@name_exists = 0, 
    'ALTER TABLE bookings ADD COLUMN attendee_name VARCHAR(100)', 
    'SELECT "Column attendee_name already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;

-- Check and add attendee_email
SELECT COUNT(*) INTO @email_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'event_booking_db' 
AND TABLE_NAME = 'bookings' 
AND COLUMN_NAME = 'attendee_email';

SET @sql = IF(@email_exists = 0, 
    'ALTER TABLE bookings ADD COLUMN attendee_email VARCHAR(100)', 
    'SELECT "Column attendee_email already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;

-- Check and add attendee_dob
SELECT COUNT(*) INTO @dob_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'event_booking_db' 
AND TABLE_NAME = 'bookings' 
AND COLUMN_NAME = 'attendee_dob';

SET @sql = IF(@dob_exists = 0, 
    'ALTER TABLE bookings ADD COLUMN attendee_dob DATE', 
    'SELECT "Column attendee_dob already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;

-- Check and add attendee_gender
SELECT COUNT(*) INTO @gender_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'event_booking_db' 
AND TABLE_NAME = 'bookings' 
AND COLUMN_NAME = 'attendee_gender';

SET @sql = IF(@gender_exists = 0, 
    'ALTER TABLE bookings ADD COLUMN attendee_gender ENUM("Male", "Female", "Other")', 
    'SELECT "Column attendee_gender already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;