-- Static demo data for the password manager DB.
-- Reset + populate: exactly 5 rows in every table.
-- VAULT_ITEM has 20 rows (5 per item type) so the type-specific child tables
-- each get 5 semantically-correct rows.
USE password_manager;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE USER;
TRUNCATE TABLE VAULT;
TRUNCATE TABLE VAULT_ITEM;
TRUNCATE TABLE PASSWORD;
TRUNCATE TABLE TOTP;
TRUNCATE TABLE PASSKEY;
TRUNCATE TABLE SECURE_NOTE;
TRUNCATE TABLE ATTACHMENT;
TRUNCATE TABLE FILE_CHUNK;
TRUNCATE TABLE CATEGORY;
TRUNCATE TABLE ITEM_CATEGORY;
TRUNCATE TABLE SHARE;
TRUNCATE TABLE AUDIT_LOG;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------- USER ----------
INSERT INTO USER (UserID, Username, Email, PasswordHash) VALUES
  (1, 'demo',   'demo@example.com',   '$2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'),
  (2, 'pepper', 'pepper@example.com', '$2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'),
  (3, 'alice',  'alice@example.com',  '$2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'),
  (4, 'bob',    'bob@example.com',    '$2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'),
  (5, 'carol',  'carol@example.com',  '$2y$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy');
-- Password for all demo users: password

-- ---------- VAULT ----------
INSERT INTO VAULT (VaultID, UserID, VaultName) VALUES
  (1, 1, 'Personal'),
  (2, 1, 'Work'),
  (3, 2, 'Personal'),
  (4, 3, 'Shared'),
  (5, 4, 'Family');

-- ---------- VAULT_ITEM ----------
-- 5 PASSWORD, 5 TOTP, 5 PASSKEY, 5 SECURE_NOTE
INSERT INTO VAULT_ITEM (ItemID, VaultID, Title, ItemType) VALUES
  ( 1, 1, 'GitHub',            'PASSWORD'),
  ( 2, 1, 'Wi-Fi Router',      'PASSWORD'),
  ( 3, 2, 'Corporate VPN',     'PASSWORD'),
  ( 4, 1, 'Netflix',           'PASSWORD'),
  ( 5, 1, 'Email Account',     'PASSWORD'),
  ( 6, 1, 'Google',            'TOTP'),
  ( 7, 1, 'GitHub 2FA',        'TOTP'),
  ( 8, 2, 'Company SSO',       'TOTP'),
  ( 9, 4, 'Slack',             'TOTP'),
  (10, 3, 'Twitter',           'TOTP'),
  (11, 1, 'Laptop Login',      'PASSKEY'),
  (12, 2, 'Corporate Laptop',  'PASSKEY'),
  (13, 4, 'Google Account',    'PASSKEY'),
  (14, 5, 'Family PC',         'PASSKEY'),
  (15, 5, 'Media Server',      'PASSKEY'),
  (16, 1, 'Meeting notes',     'SECURE_NOTE'),
  (17, 2, 'Onboarding checklist', 'SECURE_NOTE'),
  (18, 3, 'Recovery codes',    'SECURE_NOTE'),
  (19, 4, 'Team access notes', 'SECURE_NOTE'),
  (20, 5, 'House WiFi notes',  'SECURE_NOTE');

-- ---------- PASSWORD (items 1-5) ----------
-- Encrypted payloads are opaque blobs; real values are encrypted client-side.
INSERT INTO PASSWORD (ItemID, UsernameEnc, PasswordEnc, UrlEnc) VALUES
  (1, X'DEADBEEF0101010101', X'DEADBEEF0202020202', X'DEADBEEF0303030303'),
  (2, X'DEADBEEF0404040404', X'DEADBEEF0505050505', X'DEADBEEF0606060606'),
  (3, X'DEADBEEF0707070707', X'DEADBEEF0808080808', X'DEADBEEF0909090909'),
  (4, X'DEADBEEF1010101010', X'DEADBEEF1111111111', X'DEADBEEF1212121212'),
  (5, X'DEADBEEF1313131313', X'DEADBEEF1414141414', X'DEADBEEF1515151515');

-- ---------- TOTP (items 6-10) ----------
INSERT INTO TOTP (ItemID, SecretEnc, Issuer, AccountName) VALUES
  ( 6, X'FEEDFACE0606060606', 'Google',  'demo@example.com'),
  ( 7, X'FEEDFACE0707070707', 'GitHub',  'demo'),
  ( 8, X'FEEDFACE0808080808', 'Acme SSO','demo@acme.example'),
  ( 9, X'FEEDFACE0909090909', 'Slack',   'alice@example.com'),
  (10, X'FEEDFACE0A0A0A0A0A', 'Twitter', 'pepper');

-- ---------- PASSKEY (items 11-15) ----------
INSERT INTO PASSKEY (ItemID, RpId, CredentialId, PrivateKeyEnc) VALUES
  (11, 'laptop.local',      'cred-laptop-demo',    X'BAAAAAD01111111111'),
  (12, 'corp.example.com',  'cred-corp-laptop',    X'BAAAAAD02222222222'),
  (13, 'accounts.google.com','cred-google-alice',  X'BAAAAAD03333333333'),
  (14, 'family-home.net',   'cred-family-pc',      X'BAAAAAD04444444444'),
  (15, 'media-server.home', 'cred-media-server',   X'BAAAAAD05555555555');

-- ---------- SECURE_NOTE (items 16-20) ----------
INSERT INTO SECURE_NOTE (ItemID, ContentEnc) VALUES
  (16, X'CAFEBABE101010101010'),
  (17, X'CAFEBABE111111111111'),
  (18, X'CAFEBABE121212121212'),
  (19, X'CAFEBABE131313131313'),
  (20, X'CAFEBABE141414141414');

-- ---------- ATTACHMENT ----------
INSERT INTO ATTACHMENT (AttachmentID, ItemID, FileName, MimeType, FileSize) VALUES
  (1,  1, 'github-backup.txt',        'text/plain',              1234),
  (2,  2, 'router-settings.bin',      'application/octet-stream', 8192),
  (3,  6, 'totp-setup.pdf',           'application/pdf',          34567),
  (4, 11, 'passkey-info.json',        'application/json',         512),
  (5, 16, 'notes-export.md',          'text/markdown',            2048);

-- ---------- FILE_CHUNK ----------
INSERT INTO FILE_CHUNK (ChunkID, AttachmentID, ChunkNo, EncryptedData) VALUES
  (1, 1, 0, X'ACEACE000000000000'),
  (2, 1, 1, X'ACEACE111111111111'),
  (3, 1, 2, X'ACEACE222222222222'),
  (4, 2, 0, X'ACEACE333333333333'),
  (5, 2, 1, X'ACEACE444444444444');

-- ---------- CATEGORY (CategoryID = UserID keeps 1 category per user) ----------
INSERT INTO CATEGORY (CategoryID, UserID, CategoryName) VALUES
  (1, 1, 'Important'),
  (2, 1, 'Shared Apps'),
  (3, 2, 'Work'),
  (4, 3, 'Social'),
  (5, 4, 'Family');

-- ---------- ITEM_CATEGORY ----------
INSERT INTO ITEM_CATEGORY (ItemID, CategoryID) VALUES
  ( 1, 1),
  ( 2, 2),
  ( 6, 2),
  (11, 1),
  ( 3, 3);

-- ---------- SHARE ----------
INSERT INTO SHARE (ShareID, ItemID, SharedBy, SharedWith, Permission) VALUES
  (1,  1, 1, 2, 'READ'),
  (2,  3, 1, 2, 'READ_WRITE'),
  (3,  6, 1, 3, 'READ'),
  (4,  9, 3, 1, 'READ_WRITE'),
  (5, 11, 1, 4, 'READ');

-- ---------- AUDIT_LOG ----------
INSERT INTO AUDIT_LOG (LogID, UserID, ItemID, Action) VALUES
  (1, 1,  1, 'CREATED'),
  (2, 1,  2, 'UPDATED'),
  (3, 1,  6, 'READ'),
  (4, 2,  3, 'READ'),
  (5, 1, NULL, 'LOGIN');