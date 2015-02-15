<?php
include('xmlrpc.inc');

class zip_client {

	private $host;
	private $port;
	private $username;
	private $password;
	private $output_directory;
	
	function __construct($host = 'localhost', $port = 6543, $username = '', $password = '') {
		$this->host = $host;
		$this->port = $port;
		$this->username = $username;
		$this->password = $password;
		$this->output_directory = getcwd();
	}
	
	function setOutputDirectory($output_directory) {
		if (!is_dir($output_directory)) {
			mkdir($output_directory);
		}
		$this->output_directory = $output_directory;
	}
	
	/**
	 * Generate a ZIP file from a directory containing all its contents.
	 *
	 * @param string $directory: Directory containing the files to ZIP
	 * @return string $zip_filename: Filename of the generated ZIP file
	 */
	function _makeZipFromDirectory($directory) {
		$directory = realpath($directory);
		
		$zip_filename = tempnam('./', 'tmpfile');
		$handle = fopen($zip_filename, 'w');
		
		$ZF = new ZipArchive();
		if ($ZF->open($zip_filename, ZIPARCHIVE::CREATE) !== TRUE) {
			die('ERROR: Cannot open ' . $zip_filename);
		}
		if (is_dir($directory)) {
			if ($dh = opendir($directory)) {
				while (($file = readdir($dh)) !== false) {
					if (filetype($directory . '/' . $file) == 'file') {
						$ZF->addFile($directory . '/' . $file, $file);
					}
				}
				closedir($dh);
			}
		}
		$ZF->close();
		return $zip_filename;
	}

	/**
	 * Send an XMl-RPC-request
	 * 
	 * @param string $method: Name of method
	 * @param array $parameters: Parameters as an array of objects
	 * @return string: Response of XML-RPC-server
	 */
	private function xmlrpcCall($method, $parameters = array()) {
		$f = new xmlrpcmsg($method, $parameters);
		$c = new xmlrpc_client('/api/' . $method, $this->host, $this->port);
		
        $r = $c->send($f);
		if (!$r->faultCode()) {
			$v = $r->value();
			return $v->scalarval();
		} else {
			die('An error occurred (Code ' . htmlspecialchars($r->faultCode()) . '): ' . ($r->faultString()));
		}
	}

	/**
	 * XMLRPC client to SmartPrintNG server
	 *
	 * @param string $dirname: Name of directory with files
	 * @param string $converter_name: (optional) Name of converter
	 * @return string: Name of output file
	 */
	function convertZIP($dirname, $converter_name = 'princexml') {
        $zip_filename = $this->_makeZipFromDirectory($dirname);
        echo $zip_filename;
        echo "\n";
        echo filesize($zip_filename);
        echo "\n";
		$handle = fopen($zip_filename, 'r');
		$zip_data = $this->xmlrpcCall(
			'pdf', 
			array(
#				new xmlrpcval(base64_encode(fread($handle, filesize($zip_filename))), 'base64'),
				new xmlrpcval(fread($handle, filesize($zip_filename)), 'base64'),
				new xmlrpcval($converter_name, 'string')
			)
		);
		fclose($handle);

		$zip_temp = tempnam('./', 'tmpfile');
        $handle = fopen($zip_temp, 'w');
        echo $zip_data;
        echo array_keys($zip_data);
#		fwrite($handle, $zip_data->data);
		fclose($handle);
		
		$ZF = new ZipArchive();
		$ZF->open($zip_temp);
		$ZF->extractTo($this->output_directory);
		$filename = $ZF->getNameIndex(0);
		$ZF->close();
		
		unlink($zip_temp);
		unlink($zip_filename);
		return $filename;
	}
	
}

$zipClient = new zip_client('localhost', 3128);
$zipClient->setOutputDirectory('outputdir');
var_dump($zipClient->convertZIP(('/home/ajung/sandboxes/pp.server/src/pp.client/pp/client/test_data')));
#var_dump($zipClient->ping());
#var_dump($zipClient->_authenticate());
#var_dump($zipClient->availableConverters());
#var_dump($zipClient->convertZIP('ziptestdateien2'));
#var_dump($zipClient->convertZIPandRedirect('ziptestdateien2', 'pdf-prince'));
#var_dump($zipClient->convertZIPEmail('ziptestdateien2', 'pdf-prince', 'svenburkert@web.de', 'sventb@googlemail.com', 'zip client test', 'hier body'));
?>
