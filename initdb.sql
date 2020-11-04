

USE `mysql`;

CREATE DATABASE IF NOT EXISTS `demo_db` CHARACTER SET utf8 COLLATE utf8_unicode_ci;
CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY '1qaz@WSX';
GRANT ALL ON demo_db.* TO 'admin'@'%';

USE `demo_db`;

DROP TABLE IF EXISTS `data_towerlight`;
DROP TABLE IF EXISTS `data_alarm`;
DROP TABLE IF EXISTS `data_pressure`;
DROP TABLE IF EXISTS `data_status`;
DROP TABLE IF EXISTS `products`;
DROP TABLE IF EXISTS `work_orders`;
DROP TABLE IF EXISTS `wo_utypes`;
DROP TABLE IF EXISTS `alarms`;
DROP TABLE IF EXISTS `status`;
DROP TABLE IF EXISTS `machines`;
DROP TABLE IF EXISTS `formulas`;
DROP TABLE IF EXISTS `date_line`;
DROP TABLE IF EXISTS `heartbeat`;
DROP TABLE IF EXISTS `company`;



# 1. Machine
CREATE TABLE `machines` (
    `code`              VARCHAR(32)         NOT NULL,
    `machine_name`      VARCHAR(32),
    `machine_name_cn`   VARCHAR(32),
    PRIMARY KEY (`code`)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;

INSERT INTO `machines` (`code`, `machine_name`, `machine_name_cn`) VALUES
    ('toshiba001', 'auto-packing', '自動包裝機');



# 2-1 U type
CREATE TABLE `wo_utypes` (
    `id`                TINYINT(1)          NOT NULL,
    `v`                 VARCHAR(32)         NOT NULL,
    PRIMARY KEY (`id`)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;

INSERT INTO `wo_utypes` (`id`, `v`) VALUES
    (0, 's'),
    (1, 'l'),
    (2, 'b'),
    (3, 'xb');


# 3. wo
CREATE TABLE `work_orders` (
    `wo`                VARCHAR(16)         NOT NULL,
    `fk_machine_code`   VARCHAR(32)         NOT NULL,
    `dt_start`          DATETIME            NOT NULL,
    `dt_end`            DATETIME,
    `amt`               INT(11)             NOT NULL,
    PRIMARY KEY (`wo`),
    FOREIGN KEY (`fk_machine_code`)    REFERENCES `machines` (`code`),
    INDEX `dt_end` (`dt_end` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;



# 4. wo-detail
CREATE TABLE `products` (
    `serial`            VARCHAR(32)         NOT NULL,
    `fk_wo`             VARCHAR(16)         NOT NULL,
    `fk_machine_code`   VARCHAR(32)         NOT NULL,
    `fk_utype_id`       TINYINT(1)          NOT NULL,
    `dt_search`         DATETIME,
    `dt_start`          DATETIME,
    `dt_end`            DATETIME,
    PRIMARY KEY (`serial`),
    KEY `fk_wo_idx` (`fk_wo`),
    KEY `fk_machine_idx` (`fk_machine_code`),
    CONSTRAINT `fk_wo`              FOREIGN KEY (`fk_wo`)           REFERENCES `work_orders` (`wo`),
    CONSTRAINT `fk_machine_code`    FOREIGN KEY (`fk_machine_code`) REFERENCES `machines` (`code`),
    CONSTRAINT `fk_utype_id`        FOREIGN KEY (`fk_utype_id`)     REFERENCES `wo_utypes` (`id`),
    INDEX `dt_search` (`dt_search` ASC),
    INDEX `dt_end` (`dt_end` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;


# 5-1. alarm
CREATE TABLE `alarms` (
    `code`              VARCHAR(32)         NOT NULL,
    `desc`              VARCHAR(256)        NOT NULL,
    PRIMARY KEY (`code`)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;

INSERT INTO `alarms` (`code`, `desc`) VALUES
    ('333', 'continue garbage'),
    ('444', 'long alarm'),
    ('555', 'param error'),
    ('666', 'order error'),
    ('777', 'elec lock'),
    ('888', 'stock overflow');



# 5-2. Status
CREATE TABLE `status` (
    `code`              VARCHAR(32)         NOT NULL,
    `desc`              VARCHAR(256)        NOT NULL,
    `color`             CHAR(7)             NOT NULL,
    PRIMARY KEY (`code`)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;

INSERT INTO `status` (`code`, `desc`, `color`) VALUES
    ('run', '生產', '#00ff00'),
    ('mqc', '補料', '#640064'),
    ('idle', '閒置', '#ffff00'),
    ('down', '異常', '#ff0000'),
    ('poweroff', '關機', '#414141'),
    ('x', '掉資料', '#000000');



# 6-1. Pressure
CREATE TABLE `data_pressure` (
    `src`               VARCHAR(32),
    `dt`                DATETIME,
    `v`                 DECIMAL(6,2)        NOT NULL,
    PRIMARY KEY (`src`, `dt`),
    FOREIGN KEY (`src`)  REFERENCES `machines` (`code`),
    INDEX `dt` (`dt` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;



# v6-2. TowerLight
CREATE TABLE `data_towerlight` (
    `src`               VARCHAR(32),
    `kind`              VARCHAR(8),
    `dt`                DATETIME,
    `v`                 TINYINT(1)          NOT NULL,
    PRIMARY KEY (`src`, `kind`, `dt`),
    FOREIGN KEY (`src`)        REFERENCES `machines`(`code`),
    INDEX `dt` (`dt` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;


# 6-3.  Alarm
CREATE TABLE `data_alarm` (
    `id`                INT(32)             AUTO_INCREMENT,
    `src`               VARCHAR(32)         NOT NULL,
    `alarm`             VARCHAR(32)         NOT NULL,
    `dt_start`          DATETIME            NOT NULL,
    `dt_end`            DATETIME,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`src`)             REFERENCES `machines` (`code`),
    FOREIGN KEY (`alarm`)           REFERENCES `alarms` (`code`),
    INDEX `dt_start` (`dt_start` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1;


# 6-4. Status
CREATE TABLE `data_status` (
    `src`               VARCHAR(32),
    `dt`                DATETIME,
    `status`            VARCHAR(32)         NOT NULL,
    PRIMARY KEY (`src`, `dt`),
    FOREIGN KEY (`src`)     REFERENCES `machines` (`code`),
    FOREIGN KEY (`status`)  REFERENCES `status` (`code`),
    INDEX `dt` (`dt` ASC)
) CHARSET=utf8 COLLATE=utf8_unicode_ci;
