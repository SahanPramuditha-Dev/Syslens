import re

def get_playbook_suggestion(command_id: str, output: str, exit_code: int) -> str:
    """
    Analyze output of a playbook command and suggest the next diagnostic/remediation steps.
    """
    if exit_code != 0 and "cancelled" in output.lower():
        return (
            "⚠️ UAC elevation was cancelled or denied.\n"
            "👉 Next Step: Please approve the UAC elevation prompt when running this command, "
            "or start the SysLens server itself as Administrator to execute it inline."
        )

    output_lower = output.lower()

    if command_id == "sfc_scannow":
        if "did not find any integrity violations" in output_lower or "no integrity violations" in output_lower:
            return (
                "🟢 SFC check completed: No system file corruption detected.\n"
                "👉 Next Step: If you are still experiencing system instability, run 'DISM Scan Health' "
                "to inspect the underlying OS image cache."
            )
        elif "successfully repaired them" in output_lower or "repaired" in output_lower:
            return (
                "🔵 SFC check completed: Corrupted system files were detected and successfully repaired!\n"
                "👉 Next Step: Restart your computer to ensure all repaired system components are loaded."
            )
        elif "unable to fix some of them" in output_lower or "could not perform the requested operation" in output_lower:
            return (
                "🔴 SFC check failed: Corrupted system files were found but could not be repaired.\n"
                "👉 Next Step: Run 'DISM Restore Health' immediately. This will restore and repair the "
                "local Windows component store from Windows Update, after which you should run SFC again."
            )

    elif command_id == "dism_restore":
        if "completed successfully" in output_lower or "the operation completed successfully" in output_lower:
            return (
                "🟢 DISM Restore Health completed successfully: The Windows component store cache has been repaired.\n"
                "👉 Next Step: Run 'SFC Integrity Check' now to repair system files using the restored cache."
            )
        else:
            return (
                "⚠️ DISM Restore Health failed or completed with warnings.\n"
                "👉 Next Step: Verify your internet connection (needed to pull files from Windows Update) "
                "and try running 'DISM Scan Health' first."
            )

    elif command_id == "dism_scan":
        if "no component store corruption detected" in output_lower:
            return (
                "🟢 DISM Scan completed: The system image cache is healthy.\n"
                "👉 Next Step: Run 'SFC Integrity Check' to verify active system files."
            )
        elif "component store corruption" in output_lower or "corruption" in output_lower:
            return (
                "🔴 DISM Scan completed: Component store corruption was detected!\n"
                "👉 Next Step: Run 'DISM Restore Health' to download and repair the component store cache."
            )

    elif command_id == "ping_test":
        loss_match = re.search(r"(\d+)%\s+loss", output_lower)
        if loss_match:
            loss_pct = int(loss_match.group(1))
            if loss_pct > 0:
                return (
                    f"🔴 Network Packet Loss Detected: {loss_pct}% of ping packets were dropped.\n"
                    "👉 Next Step: Run 'Flush DNS Resolver Cache' and check your local router/wifi connection."
                )
        if "approximate round trip times" in output_lower or "packets: sent = 4, received = 4" in output_lower:
            return (
                "🟢 Ping test completed successfully with 0% packet loss.\n"
                "👉 Next Step: Your internet connectivity is stable. If you experience loading issues, "
                "it may be a DNS resolution latency issue. Consider flushing your DNS cache."
            )
        return (
            "⚠️ Ping test finished. Review output logs above for server response latencies.\n"
            "👉 Next Step: Run 'Flush DNS Resolver Cache' if you suspect network routing issues."
        )

    elif command_id == "flush_dns":
        if "successfully flushed" in output_lower or "successfully" in output_lower:
            return (
                "🟢 DNS Resolver Cache successfully flushed.\n"
                "👉 Next Step: Try re-accessing your web applications or browser. If connection issues persist, "
                "run 'Ping Test (google.com)' to check network-level packet loss."
            )

    elif command_id == "winsock_reset":
        if "successfully reset" in output_lower or "restart the computer" in output_lower:
            return (
                "🔵 Winsock catalog reset successfully completed.\n"
                "👉 Next Step: You must restart your computer to apply the TCP/IP stack changes."
            )

    elif command_id == "battery_report":
        if "battery report saved" in output_lower or "html" in output_lower:
            return (
                "🟢 Battery report generated successfully.\n"
                "👉 Next Step: Check your local directory for the generated battery report HTML file "
                "to review battery capacity degradation statistics."
            )

    elif command_id == "ssd_trim":
        if "retrim" in output_lower or "completed" in output_lower:
            return (
                "🟢 SSD TRIM command executed successfully.\n"
                "👉 Next Step: Storage cells optimized. No further disk cleanup required at this time."
            )

    return f"🟢 Command completed with exit code {exit_code}. Monitor system telemetry to verify improvements."
