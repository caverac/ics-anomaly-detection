use anyhow::{anyhow, Result};
use nom::{
    number::complete::{be_u16, be_u8},
    IResult,
};
use serde::Serialize;

/// Modbus TCP message structure
#[derive(Debug, Serialize)]
pub struct ModbusMessage {
    /// MBAP Header
    pub transaction_id: u16,
    pub protocol_id: u16,
    pub length: u16,
    pub unit_id: u8,

    /// PDU
    pub function_code: u8,
    pub function_name: String,
    pub is_exception: bool,
    pub exception_code: Option<u8>,

    /// Function-specific data
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_address: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub quantity: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub byte_count: Option<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub values: Option<Vec<u16>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coil_status: Option<Vec<bool>>,

    /// Raw data for unknown functions
    #[serde(skip_serializing_if = "Option::is_none")]
    pub raw_data: Option<String>,
}

/// Parse Modbus TCP message
pub fn parse(input: &[u8]) -> Result<ModbusMessage> {
    if input.len() < 8 {
        return Err(anyhow!("Modbus message too short: {} bytes", input.len()));
    }

    let (remaining, mbap) =
        parse_mbap_header(input).map_err(|e| anyhow!("Failed to parse MBAP header: {:?}", e))?;

    let (remaining, function_code) = be_u8::<_, nom::error::Error<&[u8]>>(remaining)
        .map_err(|e| anyhow!("Failed to parse function code: {:?}", e))?;

    // Check if this is an exception response
    let is_exception = function_code & 0x80 != 0;
    let actual_function_code = if is_exception {
        function_code & 0x7F
    } else {
        function_code
    };

    let function_name = get_function_name(actual_function_code);

    let mut msg = ModbusMessage {
        transaction_id: mbap.0,
        protocol_id: mbap.1,
        length: mbap.2,
        unit_id: mbap.3,
        function_code: actual_function_code,
        function_name,
        is_exception,
        exception_code: None,
        start_address: None,
        quantity: None,
        byte_count: None,
        values: None,
        coil_status: None,
        raw_data: None,
    };

    if is_exception {
        if !remaining.is_empty() {
            msg.exception_code = Some(remaining[0]);
        }
        return Ok(msg);
    }

    // Parse function-specific data
    match actual_function_code {
        // Read Coils (FC 01) - Request
        0x01 => parse_read_request(remaining, &mut msg)?,
        // Read Discrete Inputs (FC 02) - Request
        0x02 => parse_read_request(remaining, &mut msg)?,
        // Read Holding Registers (FC 03) - Request or Response
        0x03 => parse_read_registers(remaining, &mut msg)?,
        // Read Input Registers (FC 04) - Request or Response
        0x04 => parse_read_registers(remaining, &mut msg)?,
        // Write Single Coil (FC 05)
        0x05 => parse_write_single(remaining, &mut msg)?,
        // Write Single Register (FC 06)
        0x06 => parse_write_single(remaining, &mut msg)?,
        // Write Multiple Coils (FC 15)
        0x0F => parse_write_multiple(remaining, &mut msg)?,
        // Write Multiple Registers (FC 16)
        0x10 => parse_write_multiple(remaining, &mut msg)?,
        // Read Device Identification (FC 43)
        0x2B => {
            msg.raw_data = Some(hex::encode(remaining));
        }
        _ => {
            msg.raw_data = Some(hex::encode(remaining));
        }
    }

    Ok(msg)
}

/// Parse MBAP header (7 bytes)
fn parse_mbap_header(input: &[u8]) -> IResult<&[u8], (u16, u16, u16, u8)> {
    let (input, transaction_id) = be_u16(input)?;
    let (input, protocol_id) = be_u16(input)?;
    let (input, length) = be_u16(input)?;
    let (input, unit_id) = be_u8(input)?;
    Ok((input, (transaction_id, protocol_id, length, unit_id)))
}

fn parse_read_request(input: &[u8], msg: &mut ModbusMessage) -> Result<()> {
    if input.len() >= 4 {
        let (input, start_address) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse start address: {:?}", e))?;
        let (_, quantity) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse quantity: {:?}", e))?;
        msg.start_address = Some(start_address);
        msg.quantity = Some(quantity);
    }
    Ok(())
}

fn parse_read_registers(input: &[u8], msg: &mut ModbusMessage) -> Result<()> {
    if input.is_empty() {
        return Ok(());
    }

    // Could be request (4 bytes: address + quantity) or response (byte_count + data)
    if input.len() == 4 {
        // Request format
        parse_read_request(input, msg)?;
    } else if !input.is_empty() {
        // Response format
        let byte_count = input[0];
        msg.byte_count = Some(byte_count);

        if input.len() > 1 {
            let data = &input[1..];
            let mut values = Vec::new();
            for chunk in data.chunks(2) {
                if chunk.len() == 2 {
                    let value = u16::from_be_bytes([chunk[0], chunk[1]]);
                    values.push(value);
                }
            }
            if !values.is_empty() {
                msg.values = Some(values);
            }
        }
    }
    Ok(())
}

fn parse_write_single(input: &[u8], msg: &mut ModbusMessage) -> Result<()> {
    if input.len() >= 4 {
        let (input, address) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse address: {:?}", e))?;
        let (_, value) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse value: {:?}", e))?;
        msg.start_address = Some(address);
        msg.values = Some(vec![value]);
    }
    Ok(())
}

fn parse_write_multiple(input: &[u8], msg: &mut ModbusMessage) -> Result<()> {
    if input.len() >= 5 {
        let (input, address) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse address: {:?}", e))?;
        let (input, quantity) = be_u16::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse quantity: {:?}", e))?;
        let (input, byte_count) = be_u8::<_, nom::error::Error<&[u8]>>(input)
            .map_err(|e| anyhow!("Failed to parse byte count: {:?}", e))?;

        msg.start_address = Some(address);
        msg.quantity = Some(quantity);
        msg.byte_count = Some(byte_count);

        // Parse values
        let mut values = Vec::new();
        for chunk in input.chunks(2) {
            if chunk.len() == 2 {
                let value = u16::from_be_bytes([chunk[0], chunk[1]]);
                values.push(value);
            }
        }
        if !values.is_empty() {
            msg.values = Some(values);
        }
    }
    Ok(())
}

fn get_function_name(code: u8) -> String {
    match code {
        0x01 => "Read Coils".to_string(),
        0x02 => "Read Discrete Inputs".to_string(),
        0x03 => "Read Holding Registers".to_string(),
        0x04 => "Read Input Registers".to_string(),
        0x05 => "Write Single Coil".to_string(),
        0x06 => "Write Single Register".to_string(),
        0x07 => "Read Exception Status".to_string(),
        0x08 => "Diagnostics".to_string(),
        0x0B => "Get Comm Event Counter".to_string(),
        0x0C => "Get Comm Event Log".to_string(),
        0x0F => "Write Multiple Coils".to_string(),
        0x10 => "Write Multiple Registers".to_string(),
        0x11 => "Report Server ID".to_string(),
        0x14 => "Read File Record".to_string(),
        0x15 => "Write File Record".to_string(),
        0x16 => "Mask Write Register".to_string(),
        0x17 => "Read/Write Multiple Registers".to_string(),
        0x18 => "Read FIFO Queue".to_string(),
        0x2B => "Encapsulated Interface Transport".to_string(),
        _ => format!("Unknown (0x{:02X})", code),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_read_holding_registers_request() {
        // Read Holding Registers, address 0, quantity 10
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x03, // Function code
            0x00, 0x00, // Start address
            0x00, 0x0A, // Quantity
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x03);
        assert_eq!(msg.start_address, Some(0));
        assert_eq!(msg.quantity, Some(10));
        assert!(!msg.is_exception);
    }

    #[test]
    fn test_parse_read_holding_registers_response() {
        // Response with 4 register values
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x0B, // Length
            0x01, // Unit ID
            0x03, // Function code
            0x08, // Byte count
            0x00, 0x01, // Value 1
            0x00, 0x02, // Value 2
            0x00, 0x03, // Value 3
            0x00, 0x04, // Value 4
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x03);
        assert_eq!(msg.byte_count, Some(8));
        assert_eq!(msg.values, Some(vec![1, 2, 3, 4]));
    }

    #[test]
    fn test_parse_exception() {
        // Exception response
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x03, // Length
            0x01, // Unit ID
            0x83, // Function code with exception flag
            0x02, // Exception code (Illegal Data Address)
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.is_exception);
        assert_eq!(msg.function_code, 0x03);
        assert_eq!(msg.exception_code, Some(0x02));
    }

    #[test]
    fn test_parse_read_coils_request() {
        // Read Coils (FC 01), address 0, quantity 8
        let data = [
            0x00, 0x02, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x01, // Function code (Read Coils)
            0x00, 0x00, // Start address
            0x00, 0x08, // Quantity
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x01);
        assert_eq!(msg.function_name, "Read Coils");
        assert_eq!(msg.start_address, Some(0));
        assert_eq!(msg.quantity, Some(8));
    }

    #[test]
    fn test_parse_read_discrete_inputs_request() {
        // Read Discrete Inputs (FC 02)
        let data = [
            0x00, 0x03, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x02, // Function code (Read Discrete Inputs)
            0x00, 0x10, // Start address (16)
            0x00, 0x20, // Quantity (32)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x02);
        assert_eq!(msg.function_name, "Read Discrete Inputs");
        assert_eq!(msg.start_address, Some(16));
        assert_eq!(msg.quantity, Some(32));
    }

    #[test]
    fn test_parse_read_input_registers_request() {
        // Read Input Registers (FC 04)
        let data = [
            0x00, 0x04, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x04, // Function code (Read Input Registers)
            0x00, 0x08, // Start address
            0x00, 0x01, // Quantity
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x04);
        assert_eq!(msg.function_name, "Read Input Registers");
    }

    #[test]
    fn test_parse_write_single_coil() {
        // Write Single Coil (FC 05)
        let data = [
            0x00, 0x05, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x05, // Function code (Write Single Coil)
            0x00, 0x0A, // Address (10)
            0xFF, 0x00, // Value (ON)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x05);
        assert_eq!(msg.function_name, "Write Single Coil");
        assert_eq!(msg.start_address, Some(10));
        assert_eq!(msg.values, Some(vec![0xFF00]));
    }

    #[test]
    fn test_parse_write_single_register() {
        // Write Single Register (FC 06)
        let data = [
            0x00, 0x06, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x06, // Length
            0x01, // Unit ID
            0x06, // Function code (Write Single Register)
            0x00, 0x01, // Address
            0x00, 0x03, // Value (3)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x06);
        assert_eq!(msg.function_name, "Write Single Register");
        assert_eq!(msg.start_address, Some(1));
        assert_eq!(msg.values, Some(vec![3]));
    }

    #[test]
    fn test_parse_write_multiple_coils() {
        // Write Multiple Coils (FC 15)
        let data = [
            0x00, 0x07, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x08, // Length
            0x01, // Unit ID
            0x0F, // Function code (Write Multiple Coils)
            0x00, 0x13, // Start address (19)
            0x00, 0x0A, // Quantity (10)
            0x02, // Byte count
            0xCD, 0x01, // Values
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x0F);
        assert_eq!(msg.function_name, "Write Multiple Coils");
        assert_eq!(msg.start_address, Some(19));
        assert_eq!(msg.quantity, Some(10));
        assert_eq!(msg.byte_count, Some(2));
    }

    #[test]
    fn test_parse_write_multiple_registers() {
        // Write Multiple Registers (FC 16)
        let data = [
            0x00, 0x08, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x0B, // Length
            0x01, // Unit ID
            0x10, // Function code (Write Multiple Registers)
            0x00, 0x01, // Start address
            0x00, 0x02, // Quantity
            0x04, // Byte count
            0x00, 0x0A, // Value 1 (10)
            0x01, 0x02, // Value 2 (258)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x10);
        assert_eq!(msg.function_name, "Write Multiple Registers");
        assert_eq!(msg.start_address, Some(1));
        assert_eq!(msg.quantity, Some(2));
        assert_eq!(msg.byte_count, Some(4));
        assert_eq!(msg.values, Some(vec![10, 258]));
    }

    #[test]
    fn test_parse_mbap_header() {
        let data = [
            0x00, 0x01, // Transaction ID (1)
            0x00, 0x00, // Protocol ID (0)
            0x00, 0x06, // Length (6)
            0x01, // Unit ID (1)
            0x03, // Function code
            0x00, 0x00, // Extra data
            0x00, 0x0A,
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.transaction_id, 1);
        assert_eq!(msg.protocol_id, 0);
        assert_eq!(msg.length, 6);
        assert_eq!(msg.unit_id, 1);
    }

    #[test]
    fn test_parse_message_too_short() {
        let data = [0x00, 0x01, 0x00]; // Only 3 bytes
        let result = parse(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_unknown_function_code() {
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x05, // Length
            0x01, // Unit ID
            0x50, // Unknown function code
            0x01, 0x02, // Some data
            0x03, 0x04,
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x50);
        assert!(msg.function_name.starts_with("Unknown"));
        assert!(msg.raw_data.is_some());
    }

    #[test]
    fn test_parse_device_identification() {
        // Read Device Identification (FC 43)
        let data = [
            0x00, 0x09, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x05, // Length
            0x01, // Unit ID
            0x2B, // Function code (Encapsulated Interface Transport)
            0x0E, // MEI type
            0x01, // Read device ID
            0x00, // Object ID
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x2B);
        assert_eq!(msg.function_name, "Encapsulated Interface Transport");
        assert!(msg.raw_data.is_some());
    }

    #[test]
    fn test_get_function_name_all_codes() {
        assert_eq!(get_function_name(0x01), "Read Coils");
        assert_eq!(get_function_name(0x02), "Read Discrete Inputs");
        assert_eq!(get_function_name(0x03), "Read Holding Registers");
        assert_eq!(get_function_name(0x04), "Read Input Registers");
        assert_eq!(get_function_name(0x05), "Write Single Coil");
        assert_eq!(get_function_name(0x06), "Write Single Register");
        assert_eq!(get_function_name(0x07), "Read Exception Status");
        assert_eq!(get_function_name(0x08), "Diagnostics");
        assert_eq!(get_function_name(0x0B), "Get Comm Event Counter");
        assert_eq!(get_function_name(0x0C), "Get Comm Event Log");
        assert_eq!(get_function_name(0x0F), "Write Multiple Coils");
        assert_eq!(get_function_name(0x10), "Write Multiple Registers");
        assert_eq!(get_function_name(0x11), "Report Server ID");
        assert_eq!(get_function_name(0x14), "Read File Record");
        assert_eq!(get_function_name(0x15), "Write File Record");
        assert_eq!(get_function_name(0x16), "Mask Write Register");
        assert_eq!(get_function_name(0x17), "Read/Write Multiple Registers");
        assert_eq!(get_function_name(0x18), "Read FIFO Queue");
        assert_eq!(get_function_name(0x2B), "Encapsulated Interface Transport");
    }

    #[test]
    fn test_exception_without_code() {
        // Exception response without exception code
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x02, // Length
            0x01, // Unit ID
            0x81, // Function code with exception flag (FC 01)
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.is_exception);
        assert_eq!(msg.function_code, 0x01);
        assert_eq!(msg.exception_code, None);
    }

    #[test]
    fn test_empty_response() {
        let data = [
            0x00, 0x01, // Transaction ID
            0x00, 0x00, // Protocol ID
            0x00, 0x02, // Length
            0x01, // Unit ID
            0x03, // Function code (Read Holding Registers)
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.function_code, 0x03);
        assert!(msg.values.is_none());
    }
}
