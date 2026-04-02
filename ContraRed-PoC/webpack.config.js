/* eslint-disable @typescript-eslint/no-var-requires */

const devCerts = require("office-addin-dev-certs");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const path = require("path");
const webpack = require("webpack");

async function getHttpsOptions() {
    const httpsOptions = await devCerts.getHttpsServerOptions();
    return { ca: httpsOptions.ca, key: httpsOptions.key, cert: httpsOptions.cert };
}

module.exports = async (env, options) => {
    const dev = options.mode === "development";

    // Determine API URL: use env var or fall back to localhost.
    // In dev mode, proxy through the HTTPS webpack-dev-server to avoid
    // mixed-content blocks (HTTPS add-in → HTTP backend).
    if (!dev && !process.env.API_BASE_URL) {
        throw new Error('API_BASE_URL environment variable is required for production builds.');
    }
    const apiBaseUrl = process.env.API_BASE_URL || (dev ? "/api/v1" : "http://localhost:8000/api/v1");

    const config = {
        devtool: dev ? "source-map" : false,
        entry: {
            taskpane: ["./src/taskpane/taskpane.ts"],
        },
        output: {
            path: path.resolve(__dirname, "dist"),
            filename: "[name].js",
            clean: true,
        },
        resolve: {
            extensions: [".ts", ".tsx", ".html", ".js"],
        },
        module: {
            rules: [
                {
                    test: /\.ts$/,
                    exclude: /node_modules/,
                    use: "ts-loader",
                },
                {
                    test: /\.html$/,
                    exclude: /node_modules/,
                    use: "html-loader",
                },
                {
                    test: /\.css$/,
                    use: ["style-loader", "css-loader"],
                },
                {
                    test: /\.(png|jpg|jpeg|gif|ico)$/,
                    type: "asset/resource",
                    generator: {
                        filename: "assets/[name][ext]",
                    },
                },
            ],
        },
        plugins: [
            // Inject API URL at build time for Netlify env var support
            new webpack.DefinePlugin({
                "process.env.API_BASE_URL": JSON.stringify(apiBaseUrl),
                "process.env.NODE_ENV": JSON.stringify(dev ? "development" : "production"),
            }),
            new HtmlWebpackPlugin({
                filename: "taskpane.html",
                template: "./src/taskpane/taskpane.html",
                chunks: ["taskpane"],
            }),
            new HtmlWebpackPlugin({
                filename: "privacy.html",
                template: "./src/taskpane/privacy.html",
                chunks: [],
                inject: false,
            }),
            new HtmlWebpackPlugin({
                filename: "terms.html",
                template: "./src/taskpane/terms.html",
                chunks: [],
                inject: false,
            }),
            new CopyWebpackPlugin({
                patterns: [
                    {
                        from: "assets/*",
                        to: "assets/[name][ext]",
                        noErrorOnMissing: true,
                    },
                    {
                        from: "manifest*.xml",
                        to: "[name][ext]",
                    },
                ],
            }),
        ],
        devServer: {
            headers: {
                "Access-Control-Allow-Origin": "*",
            },
            server: {
                type: "https",
                options: dev ? {
                    key: require("path").resolve(require("os").homedir(), ".office-addin-dev-certs/localhost.key"),
                    cert: require("path").resolve(require("os").homedir(), ".office-addin-dev-certs/localhost.crt"),
                    ca: require("path").resolve(require("os").homedir(), ".office-addin-dev-certs/ca.crt"),
                } : {},
            },
            port: 3007,
            static: {
                directory: path.join(__dirname, "dist"),
            },
            proxy: [
                {
                    context: ["/api"],
                    target: "http://localhost:8000",
                    changeOrigin: true,
                    secure: false,
                },
                {
                    context: ["/health"],
                    target: "http://localhost:8000",
                    changeOrigin: true,
                    secure: false,
                },
            ],
        },
    };

    return config;
};
