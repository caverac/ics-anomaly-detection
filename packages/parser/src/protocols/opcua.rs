use anyhow::{anyhow, Result};
use nom::{
    bytes::complete::take,
    number::complete::{le_u32, le_u8},
    IResult,
};
use serde::Serialize;

/// OPC-UA Binary Protocol message
#[derive(Debug, Serialize)]
pub struct OpcuaMessage {
    /// Message header
    pub message_type: String,
    pub message_type_code: [u8; 3],
    pub is_final: bool,
    pub message_size: u32,

    /// Secure channel (for OPN, MSG, CLO)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub secure_channel_id: Option<u32>,

    /// For Hello messages
    #[serde(skip_serializing_if = "Option::is_none")]
    pub protocol_version: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub receive_buffer_size: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub send_buffer_size: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_message_size: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_chunk_count: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub endpoint_url: Option<String>,

    /// For MSG messages
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security_token_id: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sequence_number: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub request_id: Option<u32>,

    /// Service info
    #[serde(skip_serializing_if = "Option::is_none")]
    pub service_type: Option<String>,

    /// Raw data for detailed inspection
    #[serde(skip_serializing_if = "Option::is_none")]
    pub raw_payload: Option<String>,
}

/// Parse OPC-UA Binary Protocol message
pub fn parse(input: &[u8]) -> Result<OpcuaMessage> {
    if input.len() < 8 {
        return Err(anyhow!("OPC-UA message too short: {} bytes", input.len()));
    }

    // Parse message header
    let (remaining, header) = parse_message_header(input)
        .map_err(|e| anyhow!("Failed to parse OPC-UA header: {:?}", e))?;

    let message_type = get_message_type(&header.0);
    let is_final = header.1 == b'F';

    let mut msg = OpcuaMessage {
        message_type: message_type.clone(),
        message_type_code: header.0,
        is_final,
        message_size: header.2,
        secure_channel_id: None,
        protocol_version: None,
        receive_buffer_size: None,
        send_buffer_size: None,
        max_message_size: None,
        max_chunk_count: None,
        endpoint_url: None,
        security_token_id: None,
        sequence_number: None,
        request_id: None,
        service_type: None,
        raw_payload: None,
    };

    // Parse based on message type
    match &header.0 {
        b"HEL" => parse_hello(remaining, &mut msg)?,
        b"ACK" => parse_acknowledge(remaining, &mut msg)?,
        b"OPN" => parse_open_secure_channel(remaining, &mut msg)?,
        b"MSG" => parse_message(remaining, &mut msg)?,
        b"CLO" => parse_close_secure_channel(remaining, &mut msg)?,
        b"ERR" => parse_error(remaining, &mut msg)?,
        _ => {
            msg.raw_payload = Some(hex::encode(remaining));
        }
    }

    Ok(msg)
}

fn parse_message_header(input: &[u8]) -> IResult<&[u8], ([u8; 3], u8, u32)> {
    let (input, msg_type) = take(3usize)(input)?;
    let (input, chunk_type) = le_u8(input)?;
    let (input, msg_size) = le_u32(input)?;

    let mut type_arr = [0u8; 3];
    type_arr.copy_from_slice(msg_type);

    Ok((input, (type_arr, chunk_type, msg_size)))
}

fn parse_hello(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    if input.len() < 20 {
        msg.raw_payload = Some(hex::encode(input));
        return Ok(());
    }

    let (input, protocol_version) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse protocol version: {:?}", e))?;
    let (input, receive_buffer) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse receive buffer: {:?}", e))?;
    let (input, send_buffer) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse send buffer: {:?}", e))?;
    let (input, max_message) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse max message: {:?}", e))?;
    let (input, max_chunk) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse max chunk: {:?}", e))?;

    msg.protocol_version = Some(protocol_version);
    msg.receive_buffer_size = Some(receive_buffer);
    msg.send_buffer_size = Some(send_buffer);
    msg.max_message_size = Some(max_message);
    msg.max_chunk_count = Some(max_chunk);

    // Parse endpoint URL (length-prefixed string)
    if input.len() >= 4 {
        let (input, url_len) = le_u32::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse URL length: {:?}", e))?;

        if url_len > 0 && url_len < 4096 && input.len() >= url_len as usize {
            if let Ok(url) = std::str::from_utf8(&input[..url_len as usize]) {
                msg.endpoint_url = Some(url.to_string());
            }
        }
    }

    Ok(())
}

fn parse_acknowledge(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    if input.len() < 20 {
        msg.raw_payload = Some(hex::encode(input));
        return Ok(());
    }

    let (input, protocol_version) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse protocol version: {:?}", e))?;
    let (input, receive_buffer) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse receive buffer: {:?}", e))?;
    let (input, send_buffer) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse send buffer: {:?}", e))?;
    let (input, max_message) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse max message: {:?}", e))?;
    let (_, max_chunk) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse max chunk: {:?}", e))?;

    msg.protocol_version = Some(protocol_version);
    msg.receive_buffer_size = Some(receive_buffer);
    msg.send_buffer_size = Some(send_buffer);
    msg.max_message_size = Some(max_message);
    msg.max_chunk_count = Some(max_chunk);

    Ok(())
}

fn parse_open_secure_channel(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    if input.len() < 4 {
        msg.raw_payload = Some(hex::encode(input));
        return Ok(());
    }

    let (remaining, channel_id) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse channel ID: {:?}", e))?;

    msg.secure_channel_id = Some(channel_id);
    msg.service_type = Some("OpenSecureChannel".to_string());

    if !remaining.is_empty() {
        msg.raw_payload = Some(hex::encode(remaining));
    }

    Ok(())
}

fn parse_message(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    if input.len() < 16 {
        msg.raw_payload = Some(hex::encode(input));
        return Ok(());
    }

    let (input, channel_id) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse channel ID: {:?}", e))?;
    let (input, token_id) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse token ID: {:?}", e))?;
    let (input, seq_num) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse sequence number: {:?}", e))?;
    let (remaining, request_id) = le_u32::<_, nom::error::Error<&[u8]>>(input)
        .map_err(|e| anyhow!("Failed to parse request ID: {:?}", e))?;

    msg.secure_channel_id = Some(channel_id);
    msg.security_token_id = Some(token_id);
    msg.sequence_number = Some(seq_num);
    msg.request_id = Some(request_id);

    // Try to identify service type from node ID
    if remaining.len() >= 4 {
        // Service type is encoded as an expanded node ID
        // Simplified parsing - just store raw data for now
        msg.raw_payload = Some(hex::encode(remaining));
    }

    Ok(())
}

fn parse_close_secure_channel(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    if input.len() >= 4 {
        let (remaining, channel_id) = le_u32::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse channel ID: {:?}", e))?;
        msg.secure_channel_id = Some(channel_id);
        msg.service_type = Some("CloseSecureChannel".to_string());

        if !remaining.is_empty() {
            msg.raw_payload = Some(hex::encode(remaining));
        }
    } else {
        msg.raw_payload = Some(hex::encode(input));
    }
    Ok(())
}

fn parse_error(input: &[u8], msg: &mut OpcuaMessage) -> Result<()> {
    msg.service_type = Some("Error".to_string());
    msg.raw_payload = Some(hex::encode(input));
    Ok(())
}

fn get_message_type(code: &[u8; 3]) -> String {
    match code {
        b"HEL" => "Hello".to_string(),
        b"ACK" => "Acknowledge".to_string(),
        b"OPN" => "OpenSecureChannel".to_string(),
        b"MSG" => "Message".to_string(),
        b"CLO" => "CloseSecureChannel".to_string(),
        b"ERR" => "Error".to_string(),
        _ => format!("Unknown ({:?})", std::str::from_utf8(code).unwrap_or("???")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_hello() {
        // OPC-UA Hello message
        let data = [
            b'H', b'E', b'L', b'F', // Message type + chunk type
            0x2C, 0x00, 0x00, 0x00, // Message size (44 bytes)
            0x00, 0x00, 0x00, 0x00, // Protocol version
            0x00, 0x00, 0x01, 0x00, // Receive buffer size (65536)
            0x00, 0x00, 0x01, 0x00, // Send buffer size (65536)
            0x00, 0x00, 0x00, 0x00, // Max message size
            0x00, 0x00, 0x00, 0x00, // Max chunk count
            0x00, 0x00, 0x00, 0x00, // Endpoint URL length (0)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Hello");
        assert!(msg.is_final);
        assert_eq!(msg.protocol_version, Some(0));
    }

    #[test]
    fn test_parse_hello_with_endpoint_url() {
        // OPC-UA Hello message with endpoint URL
        let endpoint = b"opc.tcp://localhost:4840";
        let url_len = endpoint.len() as u32;

        let mut data = vec![
            b'H', b'E', b'L', b'F', // Message type + chunk type
            0x40, 0x00, 0x00, 0x00, // Message size
            0x00, 0x00, 0x00, 0x00, // Protocol version
            0x00, 0x00, 0x01, 0x00, // Receive buffer size (65536)
            0x00, 0x00, 0x01, 0x00, // Send buffer size (65536)
            0x00, 0x00, 0x00, 0x00, // Max message size
            0x00, 0x00, 0x00, 0x00, // Max chunk count
        ];
        data.extend_from_slice(&url_len.to_le_bytes());
        data.extend_from_slice(endpoint);

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Hello");
        assert_eq!(msg.endpoint_url, Some("opc.tcp://localhost:4840".to_string()));
    }

    #[test]
    fn test_parse_acknowledge() {
        // OPC-UA Acknowledge message
        let data = [
            b'A', b'C', b'K', b'F', // Message type + chunk type
            0x1C, 0x00, 0x00, 0x00, // Message size (28 bytes)
            0x00, 0x00, 0x00, 0x00, // Protocol version
            0x00, 0x00, 0x01, 0x00, // Receive buffer size (65536)
            0x00, 0x00, 0x01, 0x00, // Send buffer size (65536)
            0x00, 0x40, 0x00, 0x00, // Max message size (16384)
            0x01, 0x00, 0x00, 0x00, // Max chunk count (1)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Acknowledge");
        assert!(msg.is_final);
        assert_eq!(msg.protocol_version, Some(0));
        assert_eq!(msg.receive_buffer_size, Some(65536));
        assert_eq!(msg.send_buffer_size, Some(65536));
        assert_eq!(msg.max_message_size, Some(16384));
        assert_eq!(msg.max_chunk_count, Some(1));
    }

    #[test]
    fn test_parse_open_secure_channel() {
        // OPC-UA Open Secure Channel
        let data = [
            b'O', b'P', b'N', b'F', // Message type + chunk type
            0x20, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Secure channel ID (1)
            // Security header follows...
            0x00, 0x00, 0x00, 0x00, // Security policy length
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "OpenSecureChannel");
        assert!(msg.is_final);
        assert_eq!(msg.secure_channel_id, Some(1));
        assert_eq!(msg.service_type, Some("OpenSecureChannel".to_string()));
    }

    #[test]
    fn test_parse_message() {
        // OPC-UA Message
        let data = [
            b'M', b'S', b'G', b'F', // Message type + chunk type
            0x30, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Secure channel ID (1)
            0x02, 0x00, 0x00, 0x00, // Security token ID (2)
            0x03, 0x00, 0x00, 0x00, // Sequence number (3)
            0x04, 0x00, 0x00, 0x00, // Request ID (4)
            // Body follows...
            0x00, 0x00, 0x00, 0x00,
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Message");
        assert!(msg.is_final);
        assert_eq!(msg.secure_channel_id, Some(1));
        assert_eq!(msg.security_token_id, Some(2));
        assert_eq!(msg.sequence_number, Some(3));
        assert_eq!(msg.request_id, Some(4));
    }

    #[test]
    fn test_parse_close_secure_channel() {
        // OPC-UA Close Secure Channel
        let data = [
            b'C', b'L', b'O', b'F', // Message type + chunk type
            0x10, 0x00, 0x00, 0x00, // Message size
            0x05, 0x00, 0x00, 0x00, // Secure channel ID (5)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "CloseSecureChannel");
        assert!(msg.is_final);
        assert_eq!(msg.secure_channel_id, Some(5));
        assert_eq!(msg.service_type, Some("CloseSecureChannel".to_string()));
    }

    #[test]
    fn test_parse_error() {
        // OPC-UA Error message
        let data = [
            b'E', b'R', b'R', b'F', // Message type + chunk type
            0x10, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Error code
            0x00, 0x00, 0x00, 0x00, // Reason length
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Error");
        assert!(msg.is_final);
        assert_eq!(msg.service_type, Some("Error".to_string()));
    }

    #[test]
    fn test_parse_message_too_short() {
        let data = [b'H', b'E', b'L']; // Only 3 bytes
        let result = parse(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_unknown_message_type() {
        let data = [
            b'X', b'Y', b'Z', b'F', // Unknown message type
            0x08, 0x00, 0x00, 0x00, // Message size
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.message_type.starts_with("Unknown"));
    }

    #[test]
    fn test_parse_intermediate_chunk() {
        // OPC-UA Message with intermediate chunk type (not final)
        let data = [
            b'M', b'S', b'G', b'C', // Message type + chunk type (C = intermediate)
            0x30, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Secure channel ID
            0x02, 0x00, 0x00, 0x00, // Security token ID
            0x03, 0x00, 0x00, 0x00, // Sequence number
            0x04, 0x00, 0x00, 0x00, // Request ID
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Message");
        assert!(!msg.is_final); // Intermediate chunk
    }

    #[test]
    fn test_parse_abort_chunk() {
        // OPC-UA Message with abort chunk type
        let data = [
            b'M', b'S', b'G', b'A', // Message type + chunk type (A = abort)
            0x30, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Secure channel ID
            0x02, 0x00, 0x00, 0x00, // Security token ID
            0x03, 0x00, 0x00, 0x00, // Sequence number
            0x04, 0x00, 0x00, 0x00, // Request ID
        ];

        let msg = parse(&data).unwrap();
        assert!(!msg.is_final); // Abort is not final
    }

    #[test]
    fn test_get_message_type_all_types() {
        assert_eq!(get_message_type(b"HEL"), "Hello");
        assert_eq!(get_message_type(b"ACK"), "Acknowledge");
        assert_eq!(get_message_type(b"OPN"), "OpenSecureChannel");
        assert_eq!(get_message_type(b"MSG"), "Message");
        assert_eq!(get_message_type(b"CLO"), "CloseSecureChannel");
        assert_eq!(get_message_type(b"ERR"), "Error");
        assert!(get_message_type(b"XXX").starts_with("Unknown"));
    }

    #[test]
    fn test_parse_hello_short_payload() {
        // Hello message with payload too short for full parsing
        let data = [
            b'H', b'E', b'L', b'F', // Message type + chunk type
            0x10, 0x00, 0x00, 0x00, // Message size
            0x00, 0x00, 0x00, 0x00, // Protocol version only
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Hello");
        // Should have raw_payload since payload is too short
        assert!(msg.raw_payload.is_some());
    }

    #[test]
    fn test_parse_acknowledge_short_payload() {
        let data = [
            b'A', b'C', b'K', b'F', // Message type + chunk type
            0x10, 0x00, 0x00, 0x00, // Message size
            0x00, 0x00, 0x00, 0x00, // Not enough data
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Acknowledge");
        assert!(msg.raw_payload.is_some());
    }

    #[test]
    fn test_parse_open_secure_channel_short_payload() {
        let data = [
            b'O', b'P', b'N', b'F', // Message type + chunk type
            0x0A, 0x00, 0x00, 0x00, // Message size
            0x00, 0x00,             // Too short
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "OpenSecureChannel");
        assert!(msg.raw_payload.is_some());
    }

    #[test]
    fn test_parse_message_short_payload() {
        let data = [
            b'M', b'S', b'G', b'F', // Message type + chunk type
            0x0C, 0x00, 0x00, 0x00, // Message size
            0x01, 0x00, 0x00, 0x00, // Only secure channel ID
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "Message");
        assert!(msg.raw_payload.is_some());
    }

    #[test]
    fn test_parse_close_secure_channel_short() {
        let data = [
            b'C', b'L', b'O', b'F', // Message type + chunk type
            0x09, 0x00, 0x00, 0x00, // Message size
            0x00,                   // Too short
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_type, "CloseSecureChannel");
        assert!(msg.raw_payload.is_some());
    }

    #[test]
    fn test_message_size_parsing() {
        let data = [
            b'H', b'E', b'L', b'F', // Message type + chunk type
            0x00, 0x10, 0x00, 0x00, // Message size (4096 in little endian)
            0x00, 0x00, 0x00, 0x00, // Protocol version
            0x00, 0x00, 0x00, 0x00, // Receive buffer
            0x00, 0x00, 0x00, 0x00, // Send buffer
            0x00, 0x00, 0x00, 0x00, // Max message
            0x00, 0x00, 0x00, 0x00, // Max chunk
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.message_size, 4096);
    }

    #[test]
    fn test_opcua_message_struct_fields() {
        let msg = OpcuaMessage {
            message_type: "Hello".to_string(),
            message_type_code: [b'H', b'E', b'L'],
            is_final: true,
            message_size: 100,
            secure_channel_id: Some(1),
            protocol_version: Some(0),
            receive_buffer_size: Some(65536),
            send_buffer_size: Some(65536),
            max_message_size: Some(4096),
            max_chunk_count: Some(1),
            endpoint_url: Some("opc.tcp://localhost:4840".to_string()),
            security_token_id: None,
            sequence_number: None,
            request_id: None,
            service_type: None,
            raw_payload: None,
        };

        assert_eq!(msg.message_type, "Hello");
        assert!(msg.is_final);
        assert_eq!(msg.endpoint_url, Some("opc.tcp://localhost:4840".to_string()));
    }
}
