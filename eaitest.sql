-- MySQL dump 10.13  Distrib 5.7.17, for macos10.12 (x86_64)
--
-- Host: localhost    Database: eaitest
-- ------------------------------------------------------
-- Server version	5.7.17

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `products` (
  `pid` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `vendor` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `types` set('MUA','MSA','MTA','MDA','MSP','WEB') NOT NULL,
  PRIMARY KEY (`pid`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `results`
--

DROP TABLE IF EXISTS `results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `results` (
  `tid` int(10) unsigned NOT NULL,
  `pid` int(10) unsigned NOT NULL,
  `ttid` int(10) unsigned NOT NULL,
  `status` enum('NA','PASS','FAIL','Pending') DEFAULT NULL,
  `comments` text,
  `picture` mediumblob,
  PRIMARY KEY (`pid`,`tid`,`ttid`),
  KEY `tid` (`tid`),
  KEY `ttid` (`ttid`),
  CONSTRAINT `results_ibfk_1` FOREIGN KEY (`tid`) REFERENCES `tests` (`tid`),
  CONSTRAINT `results_ibfk_2` FOREIGN KEY (`pid`) REFERENCES `products` (`pid`),
  CONSTRAINT `results_ibfk_3` FOREIGN KEY (`ttid`) REFERENCES `testers` (`ttid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tasks`
--

DROP TABLE IF EXISTS `tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tasks` (
  `ttid` int(10) unsigned NOT NULL,
  `pid` int(10) unsigned NOT NULL,
  `testtype` enum('MUA','MSA','MTA','MDA','MSP','Web') NOT NULL,
  `state` enum('assigned','working','done') DEFAULT NULL,
  PRIMARY KEY (`ttid`,`pid`,`testtype`),
  KEY `pid` (`pid`),
  CONSTRAINT `tasks_ibfk_1` FOREIGN KEY (`ttid`) REFERENCES `testers` (`ttid`),
  CONSTRAINT `tasks_ibfk_2` FOREIGN KEY (`pid`) REFERENCES `products` (`pid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `testers`
--

DROP TABLE IF EXISTS `testers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `testers` (
  `ttid` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(255) DEFAULT NULL,
  `user` char(20) NOT NULL,
  `password` tinyblob,
  `email` varchar(255) DEFAULT NULL,
  `lastlogin` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`ttid`),
  UNIQUE KEY `user` (`user`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tests`
--

DROP TABLE IF EXISTS `tests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tests` (
  `tid` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `testid` char(11) NOT NULL,
  `testtype` enum('MUA','MSA','MTA','MDA','MSP','Web') DEFAULT NULL,
  `summary` varchar(256) NOT NULL,
  `description` text,
  `action` varchar(256) NOT NULL,
  `expected` varchar(256) NOT NULL,
  `class` enum('required','advisory') NOT NULL,
  `phase` tinyint(3) unsigned NOT NULL,
  `refs` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`tid`),
  UNIQUE KEY `testid` (`testid`)
) ENGINE=InnoDB AUTO_INCREMENT=196 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2020-10-23 12:52:12
