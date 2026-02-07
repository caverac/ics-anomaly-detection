use anyhow::{anyhow, Result};
use nom::{
    bytes::complete::take,
    number::complete::{le_u16, le_u8},
    IResult,
};
use serde::Serialize;

/// DNP3 message structure
#[derive(Debug, Serialize)]
pub struct Dnp3Message {
    /// Data Link Layer
    pub start_bytes: u16,
    pub length: u8,
    pub control: u8,
    pub destination: u16,
    pub source: u16,

    /// Control byte fields
    pub is_master: bool,
    pub frame_count_bit: bool,
    pub frame_count_valid: bool,
    pub function_code: u8,
    pub function_name: String,

    /// Transport Layer (if present)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transport_header: Option<TransportHeader>,

    /// Application Layer (if present)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub application: Option<ApplicationLayer>,

    /// Raw payload for unparsed data
    #[serde(skip_serializing_if = "Option::is_none")]
    pub raw_payload: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct TransportHeader {
    pub final_fragment: bool,
    pub first_fragment: bool,
    pub sequence: u8,
}

#[derive(Debug, Serialize)]
pub struct ApplicationLayer {
    pub control: ApplicationControl,
    pub function_code: u8,
    pub function_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub internal_indications: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub objects: Option<Vec<Dnp3Object>>,
}

#[derive(Debug, Serialize)]
pub struct ApplicationControl {
    pub final_fragment: bool,
    pub first_fragment: bool,
    pub confirm_expected: bool,
    pub unsolicited: bool,
    pub sequence: u8,
}

#[derive(Debug, Serialize)]
pub struct Dnp3Object {
    pub group: u8,
    pub variation: u8,
    pub qualifier: u8,
    pub description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub count: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<String>,
}

/// Parse DNP3 message
pub fn parse(input: &[u8]) -> Result<Dnp3Message> {
    if input.len() < 10 {
        return Err(anyhow!("DNP3 message too short: {} bytes", input.len()));
    }

    // Parse Data Link Layer header
    let (remaining, dll) = parse_data_link_header(input)
        .map_err(|e| anyhow!("Failed to parse DNP3 data link header: {:?}", e))?;

    // Verify start bytes
    if dll.0 != 0x0564 {
        return Err(anyhow!("Invalid DNP3 start bytes: 0x{:04X}", dll.0));
    }

    let control = dll.2;
    let is_master = control & 0x80 != 0;
    let frame_count_bit = control & 0x20 != 0;
    let frame_count_valid = control & 0x10 != 0;
    let function_code = control & 0x0F;
    let function_name = get_dll_function_name(function_code);

    let mut msg = Dnp3Message {
        start_bytes: dll.0,
        length: dll.1,
        control,
        destination: dll.3,
        source: dll.4,
        is_master,
        frame_count_bit,
        frame_count_valid,
        function_code,
        function_name,
        transport_header: None,
        application: None,
        raw_payload: None,
    };

    // Only parse transport/application if there's more data and it's user data
    if remaining.len() > 2 && (function_code == 0x03 || function_code == 0x04) {
        // Remove CRC bytes and parse transport layer
        if let Ok((app_data, transport)) = parse_transport_header(remaining) {
            msg.transport_header = Some(transport);

            // Parse application layer
            if app_data.len() > 2 {
                if let Ok(app) = parse_application_layer(app_data, is_master) {
                    msg.application = Some(app);
                } else {
                    msg.raw_payload = Some(hex::encode(app_data));
                }
            }
        } else {
            msg.raw_payload = Some(hex::encode(remaining));
        }
    } else if !remaining.is_empty() {
        msg.raw_payload = Some(hex::encode(remaining));
    }

    Ok(msg)
}

fn parse_data_link_header(input: &[u8]) -> IResult<&[u8], (u16, u8, u8, u16, u16)> {
    let (input, start) = le_u16(input)?;
    let (input, length) = le_u8(input)?;
    let (input, control) = le_u8(input)?;
    let (input, destination) = le_u16(input)?;
    let (input, source) = le_u16(input)?;
    // Skip CRC (2 bytes)
    let (input, _) = take(2usize)(input)?;
    Ok((input, (start, length, control, destination, source)))
}

fn parse_transport_header(input: &[u8]) -> Result<(&[u8], TransportHeader)> {
    if input.is_empty() {
        return Err(anyhow!("Empty transport data"));
    }

    let th = input[0];
    let header = TransportHeader {
        final_fragment: th & 0x80 != 0,
        first_fragment: th & 0x40 != 0,
        sequence: th & 0x3F,
    };

    Ok((&input[1..], header))
}

fn parse_application_layer(input: &[u8], is_request: bool) -> Result<ApplicationLayer> {
    if input.len() < 2 {
        return Err(anyhow!("Application layer too short"));
    }

    let ac = input[0];
    let control = ApplicationControl {
        final_fragment: ac & 0x80 != 0,
        first_fragment: ac & 0x40 != 0,
        confirm_expected: ac & 0x20 != 0,
        unsolicited: ac & 0x10 != 0,
        sequence: ac & 0x0F,
    };

    let function_code = input[1];
    let function_name = get_app_function_name(function_code);

    let mut app = ApplicationLayer {
        control,
        function_code,
        function_name,
        internal_indications: None,
        objects: None,
    };

    // Response messages have Internal Indications
    let data_start = if !is_request && input.len() >= 4 {
        let iin = u16::from_le_bytes([input[2], input[3]]);
        app.internal_indications = Some(iin);
        4
    } else {
        2
    };

    // Parse objects if present
    if input.len() > data_start {
        if let Ok(objects) = parse_objects(&input[data_start..]) {
            if !objects.is_empty() {
                app.objects = Some(objects);
            }
        }
    }

    Ok(app)
}

fn parse_objects(input: &[u8]) -> Result<Vec<Dnp3Object>> {
    let mut objects = Vec::new();
    let remaining = input;

    // Parse first object only (simplified parser - full implementation would iterate)
    if remaining.len() >= 3 {
        let group = remaining[0];
        let variation = remaining[1];
        let qualifier = remaining[2];

        let description = get_object_description(group, variation);

        let mut obj = Dnp3Object {
            group,
            variation,
            qualifier,
            description,
            count: None,
            data: None,
        };

        // Parse count based on qualifier code
        let qualifier_code = qualifier & 0x0F;
        let mut offset = 3;

        match qualifier_code {
            0x00 | 0x01 => {
                // 8-bit start/stop
                if remaining.len() >= offset + 2 {
                    let start = remaining[offset] as u16;
                    let stop = remaining[offset + 1] as u16;
                    obj.count = Some(stop - start + 1);
                    offset += 2;
                }
            }
            0x06 => {
                // All objects, no range field
            }
            0x07 | 0x08 => {
                // 8-bit or 16-bit count
                if remaining.len() > offset {
                    obj.count = Some(remaining[offset] as u16);
                    offset += 1;
                }
            }
            _ => {}
        }

        // Store remaining data as hex
        if remaining.len() > offset {
            let data_len = std::cmp::min(remaining.len() - offset, 100);
            obj.data = Some(hex::encode(&remaining[offset..offset + data_len]));
        }

        objects.push(obj);
    }

    Ok(objects)
}

fn get_dll_function_name(code: u8) -> String {
    match code {
        0x00 => "Reset Link States".to_string(),
        0x01 => "Reset User Process".to_string(),
        0x02 => "Test Link States".to_string(),
        0x03 => "Confirmed User Data".to_string(),
        0x04 => "Unconfirmed User Data".to_string(),
        0x09 => "Request Link Status".to_string(),
        0x0B => "Respond Link Status".to_string(),
        _ => format!("Unknown (0x{:02X})", code),
    }
}

fn get_app_function_name(code: u8) -> String {
    match code {
        0x00 => "Confirm".to_string(),
        0x01 => "Read".to_string(),
        0x02 => "Write".to_string(),
        0x03 => "Select".to_string(),
        0x04 => "Operate".to_string(),
        0x05 => "Direct Operate".to_string(),
        0x06 => "Direct Operate No Ack".to_string(),
        0x07 => "Immediate Freeze".to_string(),
        0x08 => "Immediate Freeze No Ack".to_string(),
        0x09 => "Freeze and Clear".to_string(),
        0x0A => "Freeze and Clear No Ack".to_string(),
        0x0B => "Freeze With Time".to_string(),
        0x0C => "Freeze With Time No Ack".to_string(),
        0x0D => "Cold Restart".to_string(),
        0x0E => "Warm Restart".to_string(),
        0x0F => "Initialize Data".to_string(),
        0x10 => "Initialize Application".to_string(),
        0x11 => "Start Application".to_string(),
        0x12 => "Stop Application".to_string(),
        0x13 => "Save Configuration".to_string(),
        0x14 => "Enable Unsolicited".to_string(),
        0x15 => "Disable Unsolicited".to_string(),
        0x16 => "Assign Class".to_string(),
        0x17 => "Delay Measure".to_string(),
        0x18 => "Record Current Time".to_string(),
        0x19 => "Open File".to_string(),
        0x1A => "Close File".to_string(),
        0x1B => "Delete File".to_string(),
        0x1C => "Get File Info".to_string(),
        0x1D => "Authenticate File".to_string(),
        0x1E => "Abort File".to_string(),
        0x81 => "Response".to_string(),
        0x82 => "Unsolicited Response".to_string(),
        _ => format!("Unknown (0x{:02X})", code),
    }
}

fn get_object_description(group: u8, variation: u8) -> String {
    match (group, variation) {
        (1, _) => "Binary Input".to_string(),
        (2, _) => "Binary Input Event".to_string(),
        (3, _) => "Double-bit Binary Input".to_string(),
        (10, _) => "Binary Output".to_string(),
        (12, _) => "Binary Output Command".to_string(),
        (20, _) => "Counter".to_string(),
        (21, _) => "Frozen Counter".to_string(),
        (30, _) => "Analog Input".to_string(),
        (32, _) => "Analog Input Event".to_string(),
        (40, _) => "Analog Output Status".to_string(),
        (41, _) => "Analog Output".to_string(),
        (50, _) => "Time and Date".to_string(),
        (60, _) => "Class Data".to_string(),
        (80, _) => "Internal Indications".to_string(),
        _ => format!("Group {} Variation {}", group, variation),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_dnp3_header() {
        // Simple DNP3 frame with header only
        let data = [
            0x64, 0x05, // Start bytes (0x0564 in little endian)
            0x05,       // Length
            0xC0,       // Control (master, unconfirmed user data)
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
        ];

        let msg = parse(&data).unwrap();
        assert_eq!(msg.start_bytes, 0x0564);
        assert!(msg.is_master);
        assert_eq!(msg.destination, 1);
        assert_eq!(msg.source, 2);
    }

    #[test]
    fn test_parse_dnp3_outstation_message() {
        // DNP3 frame from outstation (slave)
        let data = [
            0x64, 0x05, // Start bytes
            0x05,       // Length
            0x44,       // Control (outstation, unconfirmed user data)
            0x03, 0x00, // Destination
            0x04, 0x00, // Source
            0x00, 0x00, // CRC
        ];

        let msg = parse(&data).unwrap();
        assert!(!msg.is_master);
        assert_eq!(msg.destination, 3);
        assert_eq!(msg.source, 4);
        assert_eq!(msg.function_code, 0x04);
        assert_eq!(msg.function_name, "Unconfirmed User Data");
    }

    #[test]
    fn test_parse_dnp3_message_too_short() {
        let data = [0x64, 0x05, 0x05]; // Only 3 bytes
        let result = parse(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_dnp3_invalid_start_bytes() {
        let data = [
            0x00, 0x00, // Invalid start bytes
            0x05,       // Length
            0xC0,       // Control
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
        ];

        let result = parse(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_dnp3_control_byte_flags() {
        // Test frame count bit and frame count valid flags
        let data = [
            0x64, 0x05, // Start bytes
            0x05,       // Length
            0xF3,       // Control: master=1, fcb=1, fcv=1, function=3 (confirmed user data)
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.is_master);
        assert!(msg.frame_count_bit);
        assert!(msg.frame_count_valid);
        assert_eq!(msg.function_code, 0x03);
        assert_eq!(msg.function_name, "Confirmed User Data");
    }

    #[test]
    fn test_parse_dnp3_reset_link_states() {
        let data = [
            0x64, 0x05, // Start bytes
            0x05,       // Length
            0xC0,       // Control: master=1, function=0 (reset link states)
            0x01, 0x00,
            0x02, 0x00,
            0x00, 0x00,
        ];

        let msg = parse(&data).unwrap();
        // Function code is masked from control byte
        assert_eq!(msg.function_code & 0x0F, 0x00);
    }

    #[test]
    fn test_parse_dnp3_with_transport_layer() {
        // DNP3 frame with transport and application layer
        let data = [
            0x64, 0x05, // Start bytes
            0x0A,       // Length (includes transport + app)
            0xC3,       // Control: master, confirmed user data
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
            // Transport layer
            0xC0,       // Transport header: FIN=1, FIR=1, SEQ=0
            // Application layer
            0xC0,       // Application control
            0x01,       // Function code (Read)
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.transport_header.is_some());
        let th = msg.transport_header.unwrap();
        assert!(th.final_fragment);
        assert!(th.first_fragment);
        assert_eq!(th.sequence, 0);
    }

    #[test]
    fn test_parse_dnp3_with_application_layer() {
        let data = [
            0x64, 0x05, // Start bytes
            0x0C,       // Length
            0xC4,       // Control: master, unconfirmed user data
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
            // Transport layer
            0xC0,       // Transport header
            // Application layer
            0xC1,       // Application control: FIN=1, FIR=1, CON=0, UNS=0, SEQ=1
            0x01,       // Function code (Read)
            0x3C, 0x02, // IIN bytes (for response)
            0x01, 0x00, // Object header
        ];

        let msg = parse(&data).unwrap();
        assert!(msg.application.is_some());
        let app = msg.application.as_ref().unwrap();
        assert_eq!(app.function_code, 0x01);
        assert_eq!(app.function_name, "Read");
    }

    #[test]
    fn test_get_dll_function_names() {
        assert_eq!(get_dll_function_name(0x00), "Reset Link States");
        assert_eq!(get_dll_function_name(0x01), "Reset User Process");
        assert_eq!(get_dll_function_name(0x02), "Test Link States");
        assert_eq!(get_dll_function_name(0x03), "Confirmed User Data");
        assert_eq!(get_dll_function_name(0x04), "Unconfirmed User Data");
        assert_eq!(get_dll_function_name(0x09), "Request Link Status");
        assert_eq!(get_dll_function_name(0x0B), "Respond Link Status");
        assert!(get_dll_function_name(0xFF).starts_with("Unknown"));
    }

    #[test]
    fn test_get_app_function_names() {
        assert_eq!(get_app_function_name(0x00), "Confirm");
        assert_eq!(get_app_function_name(0x01), "Read");
        assert_eq!(get_app_function_name(0x02), "Write");
        assert_eq!(get_app_function_name(0x03), "Select");
        assert_eq!(get_app_function_name(0x04), "Operate");
        assert_eq!(get_app_function_name(0x05), "Direct Operate");
        assert_eq!(get_app_function_name(0x06), "Direct Operate No Ack");
        assert_eq!(get_app_function_name(0x0D), "Cold Restart");
        assert_eq!(get_app_function_name(0x0E), "Warm Restart");
        assert_eq!(get_app_function_name(0x14), "Enable Unsolicited");
        assert_eq!(get_app_function_name(0x15), "Disable Unsolicited");
        assert_eq!(get_app_function_name(0x17), "Delay Measure");
        assert_eq!(get_app_function_name(0x81), "Response");
        assert_eq!(get_app_function_name(0x82), "Unsolicited Response");
    }

    #[test]
    fn test_get_object_descriptions() {
        assert_eq!(get_object_description(1, 0), "Binary Input");
        assert_eq!(get_object_description(2, 0), "Binary Input Event");
        assert_eq!(get_object_description(3, 0), "Double-bit Binary Input");
        assert_eq!(get_object_description(10, 0), "Binary Output");
        assert_eq!(get_object_description(12, 0), "Binary Output Command");
        assert_eq!(get_object_description(20, 0), "Counter");
        assert_eq!(get_object_description(21, 0), "Frozen Counter");
        assert_eq!(get_object_description(30, 0), "Analog Input");
        assert_eq!(get_object_description(32, 0), "Analog Input Event");
        assert_eq!(get_object_description(40, 0), "Analog Output Status");
        assert_eq!(get_object_description(41, 0), "Analog Output");
        assert_eq!(get_object_description(50, 0), "Time and Date");
        assert_eq!(get_object_description(60, 0), "Class Data");
        assert_eq!(get_object_description(80, 0), "Internal Indications");
        assert!(get_object_description(99, 5).contains("Group 99"));
    }

    #[test]
    fn test_application_control_flags() {
        let ac: u8 = 0xF5; // FIN=1, FIR=1, CON=1, UNS=1, SEQ=5
        let control = ApplicationControl {
            final_fragment: ac & 0x80 != 0,
            first_fragment: ac & 0x40 != 0,
            confirm_expected: ac & 0x20 != 0,
            unsolicited: ac & 0x10 != 0,
            sequence: ac & 0x0F,
        };

        assert!(control.final_fragment);
        assert!(control.first_fragment);
        assert!(control.confirm_expected);
        assert!(control.unsolicited);
        assert_eq!(control.sequence, 5);
    }

    #[test]
    fn test_transport_header_parsing() {
        // Test transport header byte parsing
        let th: u8 = 0xC5; // FIN=1, FIR=1, SEQ=5
        let header = TransportHeader {
            final_fragment: th & 0x80 != 0,
            first_fragment: th & 0x40 != 0,
            sequence: th & 0x3F,
        };

        assert!(header.final_fragment);
        assert!(header.first_fragment);
        assert_eq!(header.sequence, 5);
    }

    #[test]
    fn test_parse_transport_header_empty() {
        let result = parse_transport_header(&[]);
        assert!(result.is_err());
    }

    #[test]
    fn test_dnp3_response_with_iin() {
        let data = [
            0x64, 0x05, // Start bytes
            0x10,       // Length
            0x44,       // Control: outstation, unconfirmed user data
            0x01, 0x00, // Destination
            0x02, 0x00, // Source
            0x00, 0x00, // CRC
            // Transport layer
            0xC0,       // Transport header
            // Application layer (response)
            0xC0,       // Application control
            0x81,       // Function code (Response)
            0x00, 0x00, // IIN bytes
        ];

        let msg = parse(&data).unwrap();
        assert!(!msg.is_master); // Outstation response
    }
}
