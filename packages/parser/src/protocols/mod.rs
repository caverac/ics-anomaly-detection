mod dnp3;
mod modbus;
mod opcua;

use anyhow::Result;
use serde::Serialize;

use crate::kafka::RawPacketMessage;

pub use dnp3::Dnp3Message;
pub use modbus::ModbusMessage;
pub use opcua::OpcuaMessage;

/// Unified parser for ICS protocols
pub struct Parser;

impl Parser {
    pub fn new() -> Self {
        Self
    }

    pub fn parse_modbus(&self, payload: &[u8], raw: &RawPacketMessage) -> Result<ParsedMessage> {
        let modbus = modbus::parse(payload)?;
        Ok(ParsedMessage::Modbus(ModbusParsedMessage {
            timestamp: raw.timestamp.clone(),
            src_ip: raw.src_ip.clone(),
            dst_ip: raw.dst_ip.clone(),
            src_port: raw.src_port,
            dst_port: raw.dst_port,
            message: modbus,
        }))
    }

    pub fn parse_dnp3(&self, payload: &[u8], raw: &RawPacketMessage) -> Result<ParsedMessage> {
        let dnp3 = dnp3::parse(payload)?;
        Ok(ParsedMessage::Dnp3(Dnp3ParsedMessage {
            timestamp: raw.timestamp.clone(),
            src_ip: raw.src_ip.clone(),
            dst_ip: raw.dst_ip.clone(),
            src_port: raw.src_port,
            dst_port: raw.dst_port,
            message: dnp3,
        }))
    }

    pub fn parse_opcua(&self, payload: &[u8], raw: &RawPacketMessage) -> Result<ParsedMessage> {
        let opcua = opcua::parse(payload)?;
        Ok(ParsedMessage::Opcua(OpcuaParsedMessage {
            timestamp: raw.timestamp.clone(),
            src_ip: raw.src_ip.clone(),
            dst_ip: raw.dst_ip.clone(),
            src_port: raw.src_port,
            dst_port: raw.dst_port,
            message: opcua,
        }))
    }
}

/// Wrapper for parsed messages with metadata
#[derive(Debug, Serialize)]
#[serde(tag = "protocol", rename_all = "snake_case")]
pub enum ParsedMessage {
    Modbus(ModbusParsedMessage),
    Dnp3(Dnp3ParsedMessage),
    Opcua(OpcuaParsedMessage),
}

#[derive(Debug, Serialize)]
pub struct ModbusParsedMessage {
    pub timestamp: String,
    pub src_ip: String,
    pub dst_ip: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub message: ModbusMessage,
}

#[derive(Debug, Serialize)]
pub struct Dnp3ParsedMessage {
    pub timestamp: String,
    pub src_ip: String,
    pub dst_ip: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub message: Dnp3Message,
}

#[derive(Debug, Serialize)]
pub struct OpcuaParsedMessage {
    pub timestamp: String,
    pub src_ip: String,
    pub dst_ip: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub message: OpcuaMessage,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kafka::RawPacketMessage;

    fn create_test_raw_message() -> RawPacketMessage {
        RawPacketMessage {
            timestamp: "2024-01-15T10:30:00Z".to_string(),
            src_ip: "192.168.1.1".to_string(),
            dst_ip: "192.168.1.2".to_string(),
            src_port: 49152,
            dst_port: 502,
            protocol: "tcp".to_string(),
            ics_protocol: "modbus".to_string(),
            payload_size: 12,
            payload_hex: "000100000006010300000a".to_string(),
        }
    }

    #[test]
    fn test_parser_new() {
        let parser = Parser::new();
        // Parser struct has no fields, just verify it can be created
        let _ = parser;
    }

    #[test]
    fn test_parse_modbus_request() {
        let parser = Parser::new();
        let raw = create_test_raw_message();

        // Read Holding Registers request
        let payload = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x03, // Function code
            0x00, 0x00, // Start address
            0x00, 0x0A, // Quantity (10)
        ];

        let result = parser.parse_modbus(&payload, &raw);
        assert!(result.is_ok());

        if let Ok(ParsedMessage::Modbus(msg)) = result {
            assert_eq!(msg.src_ip, "192.168.1.1");
            assert_eq!(msg.dst_ip, "192.168.1.2");
            assert_eq!(msg.src_port, 49152);
            assert_eq!(msg.dst_port, 502);
            assert_eq!(msg.message.function_code, 0x03);
        } else {
            panic!("Expected Modbus message");
        }
    }

    #[test]
    fn test_parse_modbus_invalid() {
        let parser = Parser::new();
        let raw = create_test_raw_message();

        // Too short
        let payload = [0x00, 0x01, 0x00];

        let result = parser.parse_modbus(&payload, &raw);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_dnp3_frame() {
        let parser = Parser::new();
        let mut raw = create_test_raw_message();
        raw.dst_port = 20000;
        raw.ics_protocol = "dnp3".to_string();

        // DNP3 frame
        let payload = [
            0x64, 0x05, // Start bytes
            0x05, // Length
            0xC0, // Control
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
        ];

        let result = parser.parse_dnp3(&payload, &raw);
        assert!(result.is_ok());

        if let Ok(ParsedMessage::Dnp3(msg)) = result {
            assert_eq!(msg.dst_port, 20000);
            assert_eq!(msg.message.start_bytes, 0x0564);
        } else {
            panic!("Expected DNP3 message");
        }
    }

    #[test]
    fn test_parse_dnp3_invalid() {
        let parser = Parser::new();
        let raw = create_test_raw_message();

        // Too short
        let payload = [0x64, 0x05];

        let result = parser.parse_dnp3(&payload, &raw);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_opcua_hello() {
        let parser = Parser::new();
        let mut raw = create_test_raw_message();
        raw.dst_port = 4840;
        raw.ics_protocol = "opcua".to_string();

        // OPC-UA Hello
        let payload = [
            b'H', b'E', b'L', b'F', 0x1C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ];

        let result = parser.parse_opcua(&payload, &raw);
        assert!(result.is_ok());

        if let Ok(ParsedMessage::Opcua(msg)) = result {
            assert_eq!(msg.dst_port, 4840);
            assert_eq!(msg.message.message_type, "Hello");
        } else {
            panic!("Expected OPC-UA message");
        }
    }

    #[test]
    fn test_parse_opcua_invalid() {
        let parser = Parser::new();
        let raw = create_test_raw_message();

        // Too short
        let payload = [b'H', b'E', b'L'];

        let result = parser.parse_opcua(&payload, &raw);
        assert!(result.is_err());
    }

    #[test]
    fn test_parsed_message_serialization() {
        let parser = Parser::new();
        let raw = create_test_raw_message();

        let payload = [
            0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x0A,
        ];

        let result = parser.parse_modbus(&payload, &raw).unwrap();
        let json = serde_json::to_string(&result).unwrap();

        assert!(json.contains("\"protocol\":\"modbus\""));
        assert!(json.contains("\"src_ip\":\"192.168.1.1\""));
        assert!(json.contains("\"function_code\":3"));
    }

    #[test]
    fn test_modbus_parsed_message_fields() {
        let msg = ModbusParsedMessage {
            timestamp: "2024-01-15T10:30:00Z".to_string(),
            src_ip: "10.0.0.1".to_string(),
            dst_ip: "10.0.0.2".to_string(),
            src_port: 49152,
            dst_port: 502,
            message: ModbusMessage {
                transaction_id: 1,
                protocol_id: 0,
                length: 6,
                unit_id: 1,
                function_code: 3,
                function_name: "Read Holding Registers".to_string(),
                is_exception: false,
                exception_code: None,
                start_address: Some(0),
                quantity: Some(10),
                byte_count: None,
                values: None,
                coil_status: None,
                raw_data: None,
            },
        };

        assert_eq!(msg.timestamp, "2024-01-15T10:30:00Z");
        assert_eq!(msg.src_ip, "10.0.0.1");
        assert_eq!(msg.dst_port, 502);
        assert_eq!(msg.message.function_code, 3);
    }

    #[test]
    fn test_dnp3_parsed_message_fields() {
        let msg = Dnp3ParsedMessage {
            timestamp: "2024-01-15T10:30:00Z".to_string(),
            src_ip: "10.0.0.1".to_string(),
            dst_ip: "10.0.0.2".to_string(),
            src_port: 49152,
            dst_port: 20000,
            message: Dnp3Message {
                start_bytes: 0x0564,
                length: 5,
                control: 0xC0,
                destination: 1,
                source: 2,
                is_master: true,
                frame_count_bit: false,
                frame_count_valid: false,
                function_code: 4,
                function_name: "Unconfirmed User Data".to_string(),
                transport_header: None,
                application: None,
                raw_payload: None,
            },
        };

        assert_eq!(msg.dst_port, 20000);
        assert_eq!(msg.message.start_bytes, 0x0564);
        assert!(msg.message.is_master);
    }

    #[test]
    fn test_opcua_parsed_message_fields() {
        let msg = OpcuaParsedMessage {
            timestamp: "2024-01-15T10:30:00Z".to_string(),
            src_ip: "10.0.0.1".to_string(),
            dst_ip: "10.0.0.2".to_string(),
            src_port: 49152,
            dst_port: 4840,
            message: OpcuaMessage {
                message_type: "Hello".to_string(),
                message_type_code: [b'H', b'E', b'L'],
                is_final: true,
                message_size: 28,
                secure_channel_id: None,
                protocol_version: Some(0),
                receive_buffer_size: Some(65536),
                send_buffer_size: Some(65536),
                max_message_size: Some(0),
                max_chunk_count: Some(0),
                endpoint_url: None,
                security_token_id: None,
                sequence_number: None,
                request_id: None,
                service_type: None,
                raw_payload: None,
            },
        };

        assert_eq!(msg.dst_port, 4840);
        assert_eq!(msg.message.message_type, "Hello");
        assert!(msg.message.is_final);
    }
}
